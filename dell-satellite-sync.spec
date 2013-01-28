Summary: Syncs Dell official repositories into RHN Satellite or Spacewalk
Name: dell-satellite-sync
Version: 1.0.1
release: 1%{?dist}
License: GPL
ExclusiveOS: Linux
Group: Applications/Dell
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch: noarch
Source0: %{name}-%{version}.tar.gz
Requires: python
ExcludeArch: s390 s390x ppc64

%description
dell-satellite-sync is a tool for taking Dell's official Linux software
repositories, syncing them into an RHN or Spacewalk server, and subscribing
registered Dell systems to the repositories' channels.

%prep
%setup -q

%install
[ ! -d %{buildroot}/usr/share/dell-satellite-sync ] && mkdir -p %{buildroot}/usr/share/dell-satellite-sync
cp dell-satellite-sync.py %{buildroot}/usr/share/dell-satellite-sync/
[ ! -d %{buildroot}/usr/bin ] && mkdir -p %{buildroot}/usr/bin
ln -sf /usr/share/dell-satellite-sync/dell-satellite-sync.py %{buildroot}/usr/bin/dell-satellite-sync
install -Dp -m0644 dell-satellite-sync.8 %{buildroot}%{_mandir}/man8/dell-satellite-sync.8
[ ! -d %{buildroot}/etc/sysconfig/dell-satellite-sync ] && mkdir -p %{buildroot}/etc/sysconfig/dell-satellite-sync
cp dell-satellite-sync.conf %{buildroot}/etc/sysconfig/dell-satellite-sync/
cp dell-system-ids %{buildroot}/etc/sysconfig/dell-satellite-sync/

%clean
[ %{buildroot} = "/" ] && exit 1
rm -rf %{buildroot}

%pre

%post

%preun

%postun
rm -rf /etc/sysconfig/dell-satellite-sync

%files
%defattr(-,root,root)
/usr/share/dell-satellite-sync/
/usr/bin/dell-satellite-sync
/etc/sysconfig/dell-satellite-sync/dell-satellite-sync.conf
/etc/sysconfig/dell-satellite-sync/dell-system-ids
%doc %{_mandir}/man8/dell-satellite-sync.8*
%doc EXAMPLES README LICENSE

%changelog
* Mon Jan 28 2013 1.0.1-1
- For a complete list of logs see /usr/share/doc/dell-satellite-sync-%{version}/README
