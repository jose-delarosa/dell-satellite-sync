#!/bin/bash

FILE_LIST="dell-satellite-sync.py LICENSE README TODO dell-satellite-sync.8"
PACKAGE_NAME=dell-satellite-sync

VERSION=$(grep "^Version:" dell-satellite-sync.spec | awk '{ print $2 }')
if [ "$VERSION" = "" ];
then
	echo "Error: Could not determine version!"
	exit 1
fi
SPEC_FILE=$PACKAGE_NAME.spec
TMP_DIR=/tmp/dss-creator-$$/$PACKAGE_NAME-$VERSION

if [ ! -f /usr/bin/rpmbuild ];
then
	echo "no /usr/bin/rpmbuild, try installing rpm-build package"
	exit 1
fi

if [ ! -d ~/src/redhat ];
then
	echo "No local src tree, creating one ..."
	mkdir -pv ~/src/redhat/{BUILD,RPMS,SOURCES,SPECS,SRPMS}
	[ "$?" = "0" ] || exit 1
	mkdir -pv ~/src/redhat/RPMS/{athlon,geode,i386,i486,i586,i686,noarch}
	[ "$?" = "0" ] || exit 1
fi

if [ ! -f ~/.rpmmacros ];
then
	echo "No .rpmmacros file, creating it now ..."
	echo -e "%packager\t$(finger $USER | grep "Name:" | awk '{ print $4 }') $USER@$HOSTNAME" > ~/.rpmmacros
	echo -e "%vendor\t\tDell" >> ~/.rpmmacros
	echo -e "%_topdir\t$HOME/src/redhat" >> ~/.rpmmacros
fi


# Now prepare files for rpm creation

for file in $FILE_LIST
do
	if [ ! -f $file ]
	then
		echo "File: [$file] is missing! Aborting!"
		exit 1
	fi
done

if [ -d $TMP_DIR ]
then
	echo "Existing tmp directory will be removed ..."
	rm -rf $TMP_DIR
	[ "$?" = "0" ] || exit 1
fi

echo "Creating tmp directory at $TMP_DIR ..."
mkdir -p $TMP_DIR
cp $FILE_LIST $TMP_DIR
pushd $TMP_DIR
cd ..
echo "Running: tar cvzf ${PACKAGE_NAME}-${VERSION}.tar.gz $PACKAGE_NAME-$VERSION/"
tar cvzf ${PACKAGE_NAME}-${VERSION}.tar.gz $PACKAGE_NAME-$VERSION/
[ "$?" = "0" ] || exit 1
popd
echo "Copying source tarball ..."
cp -fv $TMP_DIR/../$PACKAGE_NAME-$VERSION.tar.gz ~/src/redhat/SOURCES/
[ "$?" = "0" ] || exit 1
rm -rf $TMP_DIR
echo "Copying spec file ..."
cp -fv $SPEC_FILE ~/src/redhat/SPECS/
[ "$?" = "0" ] || exit 1

echo "Building rpms and source rpms"
rpmbuild -ba ~/src/redhat/SPECS/$SPEC_FILE
[ "$?" = "0" ] || exit 1
