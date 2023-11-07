# We need this because we are no longer noarch, since our bundled deps might
# conceivably need to compile arch-specific things. But we currently have no
# useful debuginfo stuff.
%global debug_package %{nil}

# Disable shebang munging for specific paths.  These files are data files.
# ansible-test munges the shebangs itself.
%global __brp_mangle_shebangs_exclude_from_file %{SOURCE2}

# RHEL and Fedora add -s to the shebang line.  We do *not* use -s -E -S or -I
# with ansible because it has many optional features which users need to
# install libraries on their own to use.  For instance, paramiko for the
# network connection plugins or winrm to talk to windows hosts.
# Set this to nil to remove -s
%define py_shbang_opts %{nil}
%define py2_shbang_opts %{nil}
%define py3_shbang_opts %{nil}

%define vendor_path %{buildroot}%{python3_sitelib}/ansible/_vendor/
%define vendor_pip %{__python3} -m pip install --no-deps -v --no-build-isolation --no-binary :all: -t %{vendor_path}

# These control which bundled dep versions we pin against
%global jinja2_version 3.1.2
%global markupsafe_version 2.1.2


Name: ansible-core
Summary: SSH-based configuration management, deployment, and task execution system
Epoch: 1
Version: 2.14.9
Release: 1%{?dist}

Group: Development/Libraries
License: GPLv3+
Source0: https://files.pythonhosted.org/packages/source/a/ansible-core/ansible-core-%{version}.tar.gz
Source1: https://github.com/ansible/ansible-documentation/archive/v%{version}/ansible-documentation-%{version}.tar.gz
Source2: ansible-test-data-files.txt

# And bundled deps
Source3: https://files.pythonhosted.org/packages/source/J/Jinja2/Jinja2-%{jinja2_version}.tar.gz
Source4: https://files.pythonhosted.org/packages/source/M/MarkupSafe/MarkupSafe-%{markupsafe_version}.tar.gz

Patch0: remove-bundled-deps-from-requirements.patch

URL: http://ansible.com

# We obsolete old ansible, and any version of ansible-base.
Obsoletes: ansible < 2.10.0
Obsoletes: ansible-base < 2.11.0

# ... and provide 'ansible' so that old packages still work without updated
# spec files.
# Provides: ansible

# Bundled provides that are sprinkled throughout the codebase.
Provides: bundled(python-backports-ssl_match_hostname) = 3.7.0.1
Provides: bundled(python-distro) = 1.6.0
Provides: bundled(python-selectors2) = 1.1.1
Provides: bundled(python-six) = 1.16.0

# Things we explicitly bundle via src rpm, and put in ansible._vendor
Provides: bundled(python-jinja2) = %{jinja2_version}
Provides: bundled(python-markupsafe) = %{markupsafe_version}

BuildRequires: python%{python3_pkgversion}-devel
BuildRequires: python%{python3_pkgversion}-docutils
BuildRequires: python%{python3_pkgversion}-pip
BuildRequires: python%{python3_pkgversion}-pyyaml
BuildRequires: python%{python3_pkgversion}-rpm-macros
BuildRequires: python%{python3_pkgversion}-setuptools
BuildRequires: python%{python3_pkgversion}-wheel
BuildRequires: make git-core gcc

Requires: git-core
Requires: python%{python3_pkgversion}-PyYAML >= 5.1
Requires: python%{python3_pkgversion}-cryptography
Requires: python%{python3_pkgversion}-packaging
Requires: python%{python3_pkgversion}-resolvelib >= 0.5.3
Requires: python%{python3_pkgversion}-resolvelib < 0.9.0
Requires: sshpass

%description
Ansible is a radically simple model-driven configuration management,
multi-node deployment, and remote task execution system. Ansible works
over SSH and does not require any software or daemons to be installed
on remote nodes. Extension modules can be written in any language and
are transferred to managed machines automatically.

%package -n ansible-test
Summary: Tool for testing ansible plugin and module code
Requires: %{name} = %{epoch}:%{version}-%{release}

%description -n ansible-test
Ansible is a radically simple model-driven configuration management,
multi-node deployment, and remote task execution system. Ansible works
over SSH and does not require any software or daemons to be installed
on remote nodes. Extension modules can be written in any language and
are transferred to managed machines automatically.

This package installs the ansible-test command for testing modules and plugins
developed for ansible.

%prep
%setup -q -b1 -b3 -b4 -n ansible-core-%{version}
%patch0 -p1

# Fix all Python shebangs recursively in ansible-test
%{py3_shebang_fix} test/lib/ansible_test

%build
%{py3_build}

%install
%{py3_install}

# Handle bundled deps:
%{vendor_pip} \
  ../Jinja2-%{jinja2_version}/ \
  ../MarkupSafe-%{markupsafe_version}/

# Create system directories that Ansible defines as default locations in
# ansible/config/base.yml
DATADIR_LOCATIONS='%{_datadir}/ansible/collections
%{_datadir}/ansible/plugins/doc_fragments
%{_datadir}/ansible/plugins/action
%{_datadir}/ansible/plugins/become
%{_datadir}/ansible/plugins/cache
%{_datadir}/ansible/plugins/callback
%{_datadir}/ansible/plugins/cliconf
%{_datadir}/ansible/plugins/connection
%{_datadir}/ansible/plugins/filter
%{_datadir}/ansible/plugins/httpapi
%{_datadir}/ansible/plugins/inventory
%{_datadir}/ansible/plugins/lookup
%{_datadir}/ansible/plugins/modules
%{_datadir}/ansible/plugins/module_utils
%{_datadir}/ansible/plugins/netconf
%{_datadir}/ansible/roles
%{_datadir}/ansible/plugins/strategy
%{_datadir}/ansible/plugins/terminal
%{_datadir}/ansible/plugins/test
%{_datadir}/ansible/plugins/vars'

UPSTREAM_DATADIR_LOCATIONS=$(grep -ri default lib/ansible/config/base.yml | tr ':' '\n' | grep '/usr/share/ansible')

if [ "$SYSTEM_LOCATIONS" != "$UPSTREAM_SYSTEM_LOCATIONS" ] ; then
	echo "The upstream Ansible datadir locations have changed.  Spec file needs to be updated"
	exit 1
fi

mkdir -p %{buildroot}%{_datadir}/ansible/plugins/
for location in $DATADIR_LOCATIONS ; do
	mkdir %{buildroot}"$location"
done
mkdir -p %{buildroot}%{_sysconfdir}/ansible/
mkdir -p %{buildroot}%{_sysconfdir}/ansible/roles/

cp ../ansible-documentation-%{version}/examples/hosts %{buildroot}%{_sysconfdir}/ansible/
cp ../ansible-documentation-%{version}/examples/ansible.cfg %{buildroot}%{_sysconfdir}/ansible/

mkdir -p %{buildroot}/%{_mandir}/man1/

mkdir -p docs/man/man1
PYTHONPATH=%{vendor_path} %{__python3} packaging/cli-doc/build.py man --output-dir docs/man/man1

cp -v docs/man/man1/*.1 %{buildroot}/%{_mandir}/man1/

cp -pr ../ansible-documentation-%{version}/docs/docsite/rst .
cp -p lib/ansible_core.egg-info/PKG-INFO .

strip --strip-unneeded %{vendor_path}/markupsafe/_speedups%{python3_ext_suffix}

%files
%defattr(-,root,root)
%{_bindir}/ansible*
%exclude %{_bindir}/ansible-test
%config(noreplace) %{_sysconfdir}/ansible/
%doc README.md PKG-INFO COPYING
%doc changelogs/CHANGELOG-v2.*.rst
%doc %{_mandir}/man1/ansible*
%{_datadir}/ansible/
%{python3_sitelib}/ansible*
%exclude %{python3_sitelib}/ansible_test
%exclude %{python3_sitelib}/ansible/_vendor/markupsafe/_speedups.c

%files -n ansible-test
%{_bindir}/ansible-test
%{python3_sitelib}/ansible_test


%changelog
* Wed Aug 16 2023 Dimitri Savineau <dsavinea@redhat.com> - 1:2.14.9-1
- ansible-core 2.14.9 release (rhbz#2232432)
- Use docs and examples from ansible-documentation project.
- Build the manpages.

* Mon Aug 14 2023 Dimitri Savineau <dsavinea@redhat.com> - 1:2.14.8-1
- ansible-core 2.14.8 release (rhbz#2231892)

* Mon Jul 17 2023 Dimitri Savineau <dsavinea@redhat.com> - 1:2.14.7-1
- ansible-core 2.14.7 release (rhbz#2221820)
- rebuild with python 3.9 (rhbz#2221820)
- remove bundled packaging, pyparsing and resolvelib.

* Tue Jul 04 2023 Dimitri Savineau <dsavinea@redhat.com> - 2.15.1-1
- ansible-core 2.15.1 release (rhbz#2219619)

* Mon May 15 2023 Dimitri Savineau <dsavinea@redhat.com> - 2.15.0-1
- ansible-core 2.15.0 release (rhbz#2204510)
- update bundled markupsafe to 2.1.2.
- update bundled packaging to 21.3.
- update bundled pyparsing to 3.0.7.
- update bundled resolvelib to 1.0.1.
- remove six runtime dependency.

* Mon Feb 13 2023 Dimitri Savineau <dsavinea@redhat.com> - 2.14.2-4
- rebuild with python 3.11 (rhbz#2169466)
- remove bundled dependencies from requirements file (rhbz#2152615)
- add bundled version of resolvelib
- use PyPi sources
- remove straightplugin
- add missing obsoletes constraint

* Wed Feb 01 2023 Dimitri Savineau <dsavinea@redhat.com> - 2.14.2-3
- fix debuginfo symbols from markupsafe dependency (rhbz#2166433)

* Wed Feb 01 2023 Christian Adams <chadams@redhat.com> - 2.14.2-2
- fix bogus date in changelog (rhbz#2165763)

* Tue Jan 31 2023 Christian Adams <chadams@redhat.com> - 2.14.2-1
- ansible-core 2.14.2 release (rhbz#2165763)

* Wed Dec 07 2022 Dimitri Savineau <dsavinea@redhat.com> - 2.14.1-1
- ansible-core 2.14.1 release (rhbz#2151593)

* Tue Nov 08 2022 Dimitri Savineau <dsavinea@redhat.com> - 2.14.0-1
- ansible-core 2.14.0 release (rhbz#2141116)

* Mon Nov 07 2022 Dimitri Savineau <dsavinea@redhat.com> - 2.13.6-1
- ansible-core 2.13.6 release (rhbz#2140778)
- fix service_facts module parsing (rhbz#2128801)

* Tue Oct 11 2022 James Marshall <jamarsha@redhat.com> - 2.13.5-1
- ansible-core 2.13.5 release (rhbz#2133912)

* Thu Oct 06 2022 Dimitri Savineau <dsavinea@redhat.com> - 2.13.4-1
- ansible-core 2.13.4 release (rhbz#2132807)

* Mon Aug 15 2022 James Marshall <jamarsha@redhat.com> - 2.13.3-1
- ansible-core 2.13.3 release (rhbz#2118458)

* Mon Jul 18 2022 James Marshall <jamarsha@redhat.com> - 2.13.2-1
- ansible-core 2.13.2 release (rhbz#2108229)

* Mon Jun 27 2022 Dimitri Savineau <dsavinea@redhat.com> - 2.13.1-2
- Update bundled jinja2 version to 3.1.2 (rhbz#2101462)

* Wed Jun 22 2022 Dimitri Savineau <dsavinea@redhat.com> - 2.13.1-1
- ansible-core 2.13.1 release (rhbz#2100242)
- add bundled version of jinja2 and markupsafe

* Mon Jun 20 2022 Dimitri Savineau <dsavinea@redhat.com> - 2.12.7-1
- ansible-core 2.12.7 release (rhbz#2099317)
- remove legacy nightly configuration

* Tue May 24 2022 James Marshall <jamarsha@redhat.com> - 2.12.6-1
- ansible-core 2.12.6 release

* Fri May 13 2022 Dimitri Savineau <dsavinea@redhat.com> - 2.12.5-2
- switch from git to git-core dependency (rhbz#2083386)

* Mon May 09 2022 Dimitri Savineau <dsavinea@redhat.com> - 2.12.5-1
- ansible-core 2.12.5 release

* Wed Apr 06 2022 James Marshall <jamarsha@redhat.com> - 2.12.4-1
- ansible-core 2.12.4 release

* Mon Mar 14 2022 Dimitri Savineau <dsavinea@redhat.com> - 2.12.3-1
- ansible-core 2.12.3 release

* Tue Feb 01 2022 Dimitri Savineau <dsavinea@redhat.com> - 2.12.2-1
- ansible-core 2.12.2 release

* Tue Dec 07 2021 James Marshall <jamarsha@redhat.com> - 2.12.1-1
- ansible-core 2.12.1-1

* Mon Nov 08 2021 Dimitri Savineau <dsavinea@redhat.com> - 2.12.0-1
- ansible-core 2.12.0-1

* Tue Oct 12 2021 Christian Adams <chadams@redhat.com> - 2.11.6-1
- ansible-core 2.11.6-1, fix CVE-2021-3620, ansible-connection module
  no long discloses sensitive info.

* Wed Oct 06 2021 Yanis Guenane <yguenane@redhat.com> - 2.11.5-3
- ansible-core 2.11.5-3, add virtual provide for straightplugin

* Wed Sep 15 2021 Josh Boyer <jwboyer@redhat.com> - 2.11.5-2
- ansible-core 2.11.5-2

* Mon Sep 13 2021 Josh Boyer <jwboyer@redhat.com> - 2.11.3-3
- Bump for build

* Wed Jul 21 2021 Paul Belanger <pabelanger@redhat.com> - 2.11.3-2
- Add git dependency for ansible-galaxy CLI command.

* Tue Jul 20 2021 Yanis Guenane <yguenane@redhat.com> - 2.11.3-1
- ansible-core 2.11.3-1

* Fri Jul 02 2021 Satoe Imaishi <simaishi@redhat.com> - 2.11.2-2
- Add man pages

* Tue Jun 29 2021 Paul Belanger <pabelanger@redhat.com> - 2.11.2-1
- ansible-core 2.11.2 released.
- Drop bundled version of resolvelib in favor of
  python38-resolvelib.

* Wed Mar 31 2021 Rick Elrod <relrod@redhat.com> - 2.11.0b4-1
- ansible-core 2.11.0 beta 4

* Thu Mar 18 2021 Rick Elrod <relrod@redhat.com> - 2.11.0b2-3
- Try adding a Provides for old ansible.

* Thu Mar 18 2021 Rick Elrod <relrod@redhat.com> - 2.11.0b2-2
- Try Obsoletes instead of Conflicts.

* Thu Mar 18 2021 Rick Elrod <relrod@redhat.com> - 2.11.0b2-1
- ansible-core 2.11.0 beta 2
- Conflict with old ansible and ansible-base.

* Thu Mar 11 2021 Rick Elrod <relrod@redhat.com> - 2.11.0b1-1
- ansible-core 2.11.0 beta 1

* Mon Nov 30 2020 Rick Elrod <relrod@redhat.com> - 2.11.0-1
- ansible-core, beta

* Wed Jun 10 2020 Rick Elrod <relrod@redhat.com> - 2.10.0-1
- ansible-base, beta
