Summary: Syncs Dell official repositories into RHN Satellite or Spacewalk
Name: dell-satellite-sync
Version: 0.4.3
release: 1%{?dist}
License: GPL
ExclusiveOS: Linux
Group: Applications/Dell
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch: noarch
Source0: %{name}-%{version}.tar.gz
Requires: python, rsync
ExcludeArch: s390 s390x ppc64

%description
dell-satellite-sync is a solution for taking Dell's official Linux software 
repositories, replicating them into an RHN Satellite or Spacewalk server,
and subscribing any registered Dell systems to the correct child channel.

%prep
%setup -q

%install
[ ! -d %{buildroot}/usr/share/dell-satellite-sync ] && mkdir -p %{buildroot}/usr/share/dell-satellite-sync
cp dell-satellite-sync.py %{buildroot}/usr/share/dell-satellite-sync/
[ ! -d %{buildroot}/usr/bin ] && mkdir -p %{buildroot}/usr/bin
ln -sf /usr/share/dell-satellite-sync/dell-satellite-sync.py %{buildroot}/usr/bin/dell-satellite-sync
install -Dp -m0644 dell-satellite-sync.8 %{buildroot}%{_mandir}/man8/dell-satellite-sync.8

%clean
[ %{buildroot} = "/" ] && exit 1
rm -rf %{buildroot}

%pre

%post

%preun

%postun

%files
%defattr(-,root,root)
/usr/share/dell-satellite-sync/
/usr/bin/dell-satellite-sync
%doc %{_mandir}/man8/dell-satellite-sync.8*
%doc README LICENSE TODO

%changelog
* Wed Nov 10 2009 Vinny Valdez <vvaldez@redhat.com> 0.4.3-1
- Expanded man page with synopsis, examples, bugs
* Sun Nov 8 2009 Scott Collier <boodle11@gmail.com> 0.4.2-1
- created the man page 
* Wed Nov 7 2009 Vinny Valdez <vvaldez@redhat.com> 0.4.1-1
- Fixed timeout values from 0.4, which were not sane
- Added abort but report success/failed clients if Ctrl+c or 2 hour timeout
- Fixed some output on client result waiting to clean it up
* Wed Nov 5 2009 Vinny Valdez <vvaldez@redhat.com> 0.4-1
- Added options "--rhel5-only" and "--rhel4-only" to work around a bug in some of the Dell rpms that are being treated as the same in Satellite
- Added option "--only-systems" that accepts a comma separated list of systems to rsync and create child channels for
- Added package removal from Satellite in the channels with --delete now
- Added --exclude-from list if --only-systems is specified
- Added --repo to specify a specific repo to pull from
- Added timestamps to output
- Fixed bug with --debug mode in version 0.3
* Tue Oct 30 2009 Vinny Valdez <vvaldez@redhat.com> 0.3-1
- Cleaned up some output on the client side actions
- Added "raise" statement if using debug in some cases
- Added summary of client actions at end of process
- Added try/except on importing modules
* Tue Oct 27 2009 Vinny Valdez <vvaldez@redhat.com> 0.2-1
- Initial package created from version 0.2 of the source script
