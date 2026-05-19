# SPDX-License-Identifier: MIT
# Copyright (C) Fedora Project Authors
# License Text: https://spdx.org/licenses/MIT.html

# Disable shebang munging for specific paths.  These files are data files.
# ansible-test munges the shebangs itself.
%global __brp_mangle_shebangs_exclude_from_file %{SOURCE2}

# RHEL and Fedora add -s to the shebang line.  We do *not* use -s -E -S or -I
# with ansible because it has many optional features which users need to
# install libraries on their own to use.  For instance, paramiko for the
# network connection plugins or winrm to talk to windows hosts.
# Set this to nil to remove -s
%define py3_shbang_opts %{nil}

%global doc_version 2.16.15

Name: ansible-core
Summary: A radically simple IT automation system
Epoch:   1
Version: 2.16.16
Release: 2%{?dist}
Group: Development/Libraries
# The main license is GPLv3+. Many of the files in lib/ansible/module_utils
# are BSD licensed. There are various files scattered throughout the codebase
# containing code under different licenses.
License: GPL-3.0-or-later AND BSD-2-Clause AND PSF-2.0 AND MIT AND Apache-2.0

Source0: https://files.pythonhosted.org/packages/source/a/ansible-core/ansible_core-%{version}.tar.gz
Source1: https://github.com/ansible/ansible-documentation/archive/v%{doc_version}/ansible-documentation-%{doc_version}.tar.gz
Source2: ansible-test-data-files.txt

%if 0%{!?centos:1} && 0%{?rhel}
Source99: telemetry.py
Patch99: telemetry.patch
%endif

Url: https://ansible.com
BuildArch: noarch

# Virtual provides for bundled libraries
# Search for `_BUNDLED_METADATA` to find them

# lib/ansible/module_utils/urls.py
# SPDX-License-Identifier: BSD-2-Clause AND PSF-2.0
Provides: bundled(python3dist(backports-ssl-match-hostname)) = 3.7.0.1

# lib/ansible/module_utils/distro/*
# SPDX-License-Identifier: Apache-2.0
Provides: bundled(python3dist(distro)) = 1.6.0

# lib/ansible/module_utils/six/*
# SPDX-License-Identifier: MIT
Provides: bundled(python3dist(six)) = 1.16.0

# lib/ansible/module_utils/compat/selectors.py
# SPDX-License-Identifier: GPL-3.0-or-later
Provides: bundled(python3dist(selectors2)) = 1.1.1

# We obsolete old ansible, and any version of ansible-base.
Obsoletes: ansible < 2.10.0
Obsoletes: ansible-base < 2.11.0

BuildRequires: git-core
BuildRequires: make
BuildRequires: pyproject-rpm-macros
BuildRequires: python%{python3_pkgversion}-devel
BuildRequires: python%{python3_pkgversion}-docutils
BuildRequires: python%{python3_pkgversion}-jinja2
BuildRequires: python%{python3_pkgversion}-pip
BuildRequires: python%{python3_pkgversion}-pyyaml
BuildRequires: python%{python3_pkgversion}-rpm-macros
BuildRequires: python%{python3_pkgversion}-setuptools
BuildRequires: python%{python3_pkgversion}-wheel

Requires: git-core
Requires: python%{python3_pkgversion}-cryptography
Requires: python%{python3_pkgversion}-jinja2 >= 3.0.0
Requires: python%{python3_pkgversion}-packaging
Requires: python%{python3_pkgversion}-pyyaml >= 5.1
Requires: python%{python3_pkgversion}-resolvelib >= 0.5.3
Requires: python%{python3_pkgversion}-resolvelib < 1.1.0

%global _description %{expand:
Ansible is a radically simple model-driven configuration management,
multi-node deployment, and remote task execution system. Ansible works
over SSH and does not require any software or daemons to be installed
on remote nodes. Extension modules can be written in any language and
are transferred to managed machines automatically.}

%description %_description

%package -n ansible-test
Summary: Tool for testing ansible plugin and module code
Requires: %{name} = %{epoch}:%{version}-%{release}

%description -n ansible-test %_description

This package installs the ansible-test command for testing modules and plugins
developed for ansible.

%prep
%autosetup -N -n ansible_core-%{version} -a1

# Fix all Python shebangs recursively in ansible-test
%{py3_shebang_fix} test/lib/ansible_test

%if 0%{!?centos:1} && 0%{?rhel}
%patch -P99 -p1
%{py3_shebang_fix} %{SOURCE99}
%endif

%build
%{pyproject_wheel}

# Build manpages
mkdir -p docs/man/man1
%{python3} packaging/cli-doc/build.py man --output-dir docs/man/man1

%install
%{pyproject_install}

# Create system directories that Ansible defines as default locations in
# ansible/config/base.yml
DATADIR_LOCATIONS='%{_datadir}/ansible/collections
%{_datadir}/ansible/collections/ansible_collections
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

cp ansible-documentation-%{doc_version}/examples/hosts %{buildroot}%{_sysconfdir}/ansible/
cp ansible-documentation-%{doc_version}/examples/ansible.cfg %{buildroot}%{_sysconfdir}/ansible/

%if 0%{!?centos:1} && 0%{?rhel}
mkdir -p %{buildroot}%{_datadir}/ansible/telemetry
cp %{SOURCE99} %{buildroot}%{_datadir}/ansible/telemetry/
%py_byte_compile %{__python3} %{buildroot}%{_datadir}/ansible/telemetry/telemetry.py
%endif

mkdir -p %{buildroot}/%{_mandir}/man1
cp -v docs/man/man1/*.1 %{buildroot}/%{_mandir}/man1/

# We install licenses in this manner so we don't miss new licenses:
  # 1. Copy all files in licenses to %%{_pkglicensedir}.
  # 2. List the files explicitly in %%files.
  # 3. The build will fail with unpackaged file errors if license
  #    files aren't accounted for.
%global _pkglicensedir %{_licensedir}/ansible-core
install -Dpm 0644 licenses/* -t %{buildroot}%{_pkglicensedir}

%files
%defattr(-,root,root)
%license COPYING
%license %{_pkglicensedir}/{Apache-License,MIT-license,PSF-license,simplified_bsd}.txt
%doc README.md changelogs/CHANGELOG-v2.1?.rst
%dir %{_sysconfdir}/ansible/
%config(noreplace) %{_sysconfdir}/ansible/*
%{_bindir}/ansible*
%{_datadir}/ansible/
%{_mandir}/man1/ansible*
%{python3_sitelib}/ansible*
%exclude %{_bindir}/ansible-test
%exclude %{python3_sitelib}/ansible_test

%files -n ansible-test
%{_bindir}/ansible-test
%{python3_sitelib}/ansible_test

%changelog
* Tue Feb 10 2026 Dimitri Savineau <dsavinea@redhat.com> - 1:2.16.16-2
- Fix selinux AVC denial when telemetry is enabled (RHEL-148292)

* Tue Feb 03 2026 Dimitri Savineau <dsavinea@redhat.com> - 1:2.16.16-1
- ansible-core 2.16.16 release (RHEL-145990)

* Tue Dec 16 2025 Dimitri Savineau <dsavinea@redhat.com> - 1:2.16.15-1
- ansible-core 2.16.15 release (RHEL-136245)

* Mon Oct 27 2025 Dimitri Savineau <dsavinea@redhat.com> - 1:2.16.14-2
- Add telemetry for RHEL (RHEL-123004)

* Mon Dec 02 2024 Dimitri Savineau <dsavinea@redhat.com> - 1:2.16.14-1
- ansible-core 2.16.14 release (RHEL-69763)
- Fix CVE-2024-11079 (Unsafe Tagging Bypass via hostvars Object in
  Ansible-Core) (RHEL-66996)

* Tue Nov 26 2024 Dimitri Savineau <dsavinea@redhat.com> - 1:2.16.13-1
- ansible-core 2.16.13 release (RHEL-69036)
- Add back ansible-test subpackage and drop doc subpackage
- Fix CVE-2024-8775 (Exposure of Sensitive Information in Ansible
  Vault Files Due to Improper Logging) (RHEL-59076)
- Fix CVE-2024-9902 (Ansible-core user may read/write unauthorized
  content) (RHEL-69034)

* Tue Oct 29 2024 Troy Dawson <tdawson@redhat.com> - 1:2.16.3-4
- Bump release for October 2024 mass rebuild:
  Resolves: RHEL-64018

* Thu Jul 25 2024 Brian Stinson <bstinson@redhat.com> - 1:2.16.3-3
- Bump the Epoch to preserve upgrade path with previous versions of RHEL 

* Mon Jun 24 2024 Troy Dawson <tdawson@redhat.com> - 2.16.3-2
- Bump release for June 2024 mass rebuild

* Thu Feb 01 2024 Maxwell G <maxwell@gtmx.me> - 2.16.3-1
- Update to 2.16.3. Fixes rhbz#2261507.

* Mon Jan 22 2024 Fedora Release Engineering <releng@fedoraproject.org> - 2.16.2-4
- Rebuilt for https://fedoraproject.org/wiki/Fedora_40_Mass_Rebuild

* Fri Jan 19 2024 Fedora Release Engineering <releng@fedoraproject.org> - 2.16.2-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_40_Mass_Rebuild

* Thu Jan 18 2024 Maxwell G <maxwell@gtmx.me> - 2.16.2-2
- Mitigate CVE-2024-0690.

* Mon Dec 11 2023 Maxwell G <maxwell@gtmx.me> - 2.16.2-1
- Update to 2.16.2. Fixes rhbz#2254093.

* Wed Dec 06 2023 Maxwell G <maxwell@gtmx.me> - 2.16.1-1
- Update to 2.16.1. Fixes rhbz#2252860.

* Fri Nov 10 2023 Maxwell G <maxwell@gtmx.me> - 2.16.0-1
- Update to 2.16.0. Fixes rhbz#2248187.

* Thu Oct 19 2023 Maxwell G <maxwell@gtmx.me> - 2.16.0~rc1-1
- Update to 2.16.0~rc1.

* Tue Oct 03 2023 Maxwell G <maxwell@gtmx.me> - 2.16.0~b2-1
- Update to 2.16.0~b2.

* Mon Oct 02 2023 Miro Hrončok <mhroncok@redhat.com> - 2.16.0~b1-2
- Do not use tomcli in Fedora ELN, avoid pulling unwanted dependencies

* Wed Sep 27 2023 Maxwell G <maxwell@gtmx.me> - 2.16.0~b1-1
- Update to 2.16.0~b1.

* Tue Sep 26 2023 Kevin Fenzi <kevin@scrye.com> - 2.15.4-2
- Add patch to fix readfp with python-3.12. Fixes rhbz#2239728

* Mon Sep 11 2023 Maxwell G <maxwell@gtmx.me> - 2.15.4-1
- Update to 2.15.4. Fixes rhbz#2238445.

* Thu Aug 17 2023 Maxwell G <maxwell@gtmx.me> - 2.15.3-1
- Update to 2.15.3. Fixes rhbz#2231963.

* Wed Jul 19 2023 Fedora Release Engineering <releng@fedoraproject.org> - 2.15.2-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_39_Mass_Rebuild

* Tue Jul 18 2023 Maxwell G <maxwell@gtmx.me> - 2.15.2-1
- Update to 2.15.2. Fixes rhbz#2223469.
- Use the docs sources from https://github.com/ansible/ansible-documentation.

* Mon Jul 03 2023 Maxwell G <maxwell@gtmx.me> - 2.15.1-2
- Rebuilt for Python 3.12

* Thu Jun 22 2023 Maxwell G <maxwell@gtmx.me> - 2.15.1-1
- Update to 2.15.1. Fixes rhbz#2204492.
- Add Recommends on python3-libdnf5 for Fedora 39

* Sat Jun 17 2023 Maxwell G <maxwell@gtmx.me> - 2.15.0-5
- Add patch to avoid importlib.abc.TraversableResources DeprecationWarning

* Fri Jun 16 2023 Python Maint <python-maint@redhat.com> - 2.15.0-4
- Rebuilt for Python 3.12

* Tue Jun 13 2023 Maxwell G <maxwell@gtmx.me> - 2.15.0-3
- Add support for Python 3.12. Fixes rhbz#2196539.
- Remove conditional Requires on ansible-packaging.

* Tue May 23 2023 Yaakov Selkowitz <yselkowi@redhat.com> - 2.15.0-2
- Disable tests in RHEL builds

* Tue May 16 2023 Maxwell G <maxwell@gtmx.me> - 2.15.0-1
- Update to 2.15.0.
- Don't remove dotfiles and empty files. ansible-core actually needs these.

* Wed May 03 2023 Maxwell G <maxwell@gtmx.me> - 2.15.0~rc2-1
- Update to 2.15.0~rc2.

* Thu Apr 27 2023 Maxwell G <maxwell@gtmx.me> - 2.15.0~rc1-1
- Update to 2.15.0~rc1.

* Mon Apr 24 2023 Maxwell G <maxwell@gtmx.me> - 2.15.0~b3-1
- Update to 2.15.0~b3.
- Account for the removed Makefile

* Mon Apr 24 2023 Maxwell G <maxwell@gtmx.me> - 2.14.4-2
- Add gating

* Wed Mar 29 2023 Maxwell G <maxwell@gtmx.me> - 2.14.4-1
- Update to 2.14.4. Fixes rhbz#2173765.

* Wed Mar 01 2023 Maxwell G <maxwell@gtmx.me> - 2.14.3-1
- Update to 2.14.3.

* Tue Jan 31 2023 David Moreau-Simard <moi@dmsimard.com> - 2.14.2-1
- Update to 2.14.2. Fixes rhbz#2165629.

* Wed Jan 18 2023 Fedora Release Engineering <releng@fedoraproject.org> - 2.14.1-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_38_Mass_Rebuild

* Fri Dec 09 2022 Maxwell G <gotmax@e.email> - 2.14.1-1
- Update to 2.14.1.

* Mon Nov 07 2022 Maxwell G <gotmax@e.email> - 2.14.0-1
- Update to 2.14.0.

* Wed Nov 02 2022 Maxwell G <gotmax@e.email> - 2.14.0~rc2-1
- Update to 2.14.0~rc2.

* Fri Oct 28 2022 Maxwell G <gotmax@e.email> - 2.14.0~rc1-1
- Update to 2.14.0~rc1.

* Wed Oct 12 2022 Maxwell G <gotmax@e.email> - 2.13.5-1
- Update to 2.13.5.

* Tue Sep 13 2022 Maxwell G <gotmax@e.email> - 2.13.4-1
- Update to 2.13.4.

* Wed Aug 31 2022 Maxwell G <gotmax@e.email> - 2.13.3-2
- Remove weak deps on paramiko and winrm

* Mon Aug 15 2022 Maxwell G <gotmax@e.email> - 2.13.3-1
- Update to 2.13.3.

* Wed Jul 20 2022 Fedora Release Engineering <releng@fedoraproject.org> - 2.13.2-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_37_Mass_Rebuild

* Tue Jul 19 2022 Maxwell G <gotmax@e.email> - 2.13.2-1
- Update to 2.13.2. Fixes rhbz#2108195.

* Thu Jul 07 2022 Miro Hrončok <mhroncok@redhat.com> - 2.13.1-2
- Don't put -- into Python shebangs

* Wed Jun 22 2022 Maxwell G <gotmax@e.email> - 2.13.1-1
- Update to 2.13.1 (rhbz#2096312).

* Thu Jun 16 2022 Maxwell G <gotmax@e.email> - 2.13.0-1
- Update to 2.13.0.
- Re-enable tests that work with newer pytest
- Patch out python3-mock
- Manually build manpages to workaround upstream issue.
- Remove unneeded BRs and switch to pyproject-rpm-macros.
- Make ansible-base* Obsoletes/Provides compliant with Packaging Guidelines
- Remove python3-jmespath dependency. json_query is part of community.general.
- Correct licensing
- Generate shell completions

* Thu Jun 16 2022 Python Maint <python-maint@redhat.com> - 2.12.6-2
- Rebuilt for Python 3.11

* Tue May 24 2022 Maxwell G <gotmax@e.email> - 2.12.6-1
- Update to 2.12.6.

* Wed Apr 27 2022 Maxwell G <gotmax@e.email> - 2.12.5-1
- Update to 2.12.5. Fixes rhbz#2078558.

* Sat Apr 02 2022 Maxwell G <gotmax@e.email> - 2.12.4-1
- Update to 2.12.4. Fixes rhbz#2069384.

* Thu Mar 10 2022 Maxwell G <gotmax@e.email> - 2.12.3-2
- Add patch to fix failing tests and FTBFS with Pytest 7.
- Resolves: rhbz#2059937

* Tue Mar 01 2022 Kevin Fenzi <kevin@scrye.com> - 2.12.3-1
- Update to 2.12.3. Fixes rhbz#2059284

* Mon Jan 31 2022 Kevin Fenzi <kevin@scrye.com> - 2.12.2-1
- Update to 2.12.2. Fixes rhbz#2048795

* Wed Jan 19 2022 Fedora Release Engineering <releng@fedoraproject.org> - 2.12.1-4
- Rebuilt for https://fedoraproject.org/wiki/Fedora_36_Mass_Rebuild

* Thu Jan 13 2022 Neal Gompa <ngompa@fedoraproject.org> - 2.12.1-3
- Split out packaging macros and generators to ansible-packaging

* Wed Dec 08 2021 Kevin Fenzi <kevin@scrye.com> - 2.12.1-2
- Re-enable tests

* Tue Dec 07 2021 Kevin Fenzi <kevin@scrye.com> - 2.12.1-1
- Update to 2.12.1. Fixes rhbz#2029598

* Mon Nov 08 2021 Kevin Fenzi <kevin@scrye.com> - 2.12.0-1
- Update to 2.12.0. Fixes rhbz#2022533

* Thu Oct 14 2021 Maxwell G <gotmax@e.email> - 2.11.6-1
- Update to 2.11.6.

* Tue Sep 14 2021 Kevin Fenzi <kevin@scrye.com> - 2.11.5-1
- Update to 2.11.5. Fixes rhbz#2002393

* Thu Aug 19 2021 Kevin Fenzi <kevin@scrye.com> - 2.11.4-1
- Update to 2.11.4. Fixes rhbz#1994107

* Sun Jul 25 2021 Kevin Fenzi <kevin@scrye.com> - 2.11.3-1
- Update to 2.11.3. Fixes rhbz#1983836

* Wed Jul 21 2021 Fedora Release Engineering <releng@fedoraproject.org> - 2.11.2-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_35_Mass_Rebuild

* Tue Jun 22 2021 Kevin Fenzi <kevin@scrye.com> - 2.11.2-1
- Update to 2.11.2. Fixed rhbz#1974593

* Fri Jun 04 2021 Python Maint <python-maint@redhat.com> - 2.11.1-2
- Rebuilt for Python 3.10

* Mon May 24 2021 Kevin Fenzi <kevin@scrye.com> - 2.11.1-1
- Update to 2.11.1. Fixes rhbz#1964172

* Tue Apr 27 2021 Kevin Fenzi <kevin@scrye.com> - 2.11.0-1
- Update to 2.11.0 final.

* Sat Apr 24 2021 Kevin Fenzi <kevin@scrye.com> - 2.11.0-0.3.rc2
- Update to 2.11.0rc2.

* Sat Apr 03 2021 Kevin Fenzi <kevin@scrye.com> - 2.11.0-0.1.b4
- Rename to ansible-base, update to b4 beta version.

* Sat Feb 20 2021 Kevin Fenzi <kevin@scrye.com> - 2.10.6-1
- Update to 2.10.6.
- Fixes CVE-2021-20228

* Tue Jan 26 2021 Fedora Release Engineering <releng@fedoraproject.org> - 2.10.5-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_34_Mass_Rebuild

* Sun Jan 24 2021 Kevin Fenzi <kevin@scrye.com> - 2.10.5-1
- Update to 2.10.5.

* Sat Dec 19 2020 Kevin Fenzi <kevin@scrye.com> - 2.10.4-1
- Update to 2.10.4

* Sat Nov 07 2020 Kevin Fenzi <kevin@scrye.com> - 2.10.3-2
- Various review fixes

* Tue Nov 03 2020 Kevin Fenzi <kevin@scrye.com> - 2.10.3-1
- Update to 2.10.3

* Sat Oct 10 2020 Kevin Fenzi <kevin@scrye.com> - 2.10.2-1
- Update to 2.10.2

* Sat Sep 26 2020 Kevin Fenzi <kevin@scrye.com> - 2.10.1-1
- Initial version for review.

