#! /usr/bin/env python

import os, logging, re, stat
from parseconf import *

class TestError(Exception):
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return '<Test Error: %s>' % self.name

class StripccError(Exception):
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return '<Stripcc Error: %s>' % self.name

def wcl(file):
    lineCount = 0
    fp = open(file, 'r')
    while fp.readline() != '':
        lineCount += 1
    fp.close()
    return lineCount

def totalCode(dir):
    exts = ['h', 'c']
    amount = 0
    # statistic
    entries = os.listdir(dir)
    for entry in entries:
        path = '%s/%s' % (dir, entry)
        st = os.lstat(path)
        if stat.S_ISDIR(st.st_mode):
            amount += totalCode(path)
        elif stat.S_ISREG(st.st_mode):
            if path.find('.') != -1:
                ext = path.rpartition('.')[2]
                if ext in exts:
                    amount += wcl(path)
    return amount

def test(stripcc):
    packageDir = os.getcwd()

    # read package's info
    pc = ParseConf('./script')
    # get package
    package = pc.getValue('package')
    # get topdir
    try:
        topdir = pc.getValue('topdir')
    except NameNotExisted:
        topdir = package.partition('.tar')[0]
    # get pre_make
    try:
        pre_make = pc.getValue('pre_make')
    except NameNotExisted:
        pre_make = './configure'
    # get make
    try:
        make = pc.getValue('make')
    except NameNotExisted:
        make = 'make'
    # get make_dir
    try:
        make_dir = pc.getValue('make_dir')
    except NameNotExisted:
        make_dir = None
    # get clean
    try:
        clean = pc.getValue('clean')
    except NameNotExisted:
        clean = 'make clean'

    # clear
    if os.path.exists(topdir):
        os.system('rm -rf %s' % topdir)
    # decompress
    if package.endswith('.gz'):
        ret = os.system('tar zxf %s' % package)
    elif package.endswith('.bz2'):
        ret = os.system('tar jxf %s' % package)
    else:
        # unknow package's type
        raise TestError('Unknow package\'s type')
    if ret != 0:
        raise TestError('Failed to decompress')
    # change to topdir
    os.chdir(topdir)
    # get totalCode before strip
    codeAmount = totalCode('.')
    # prepare to make
    if os.system(pre_make) != 0:
        raise TestError('Failed to prepare for make')
    # make and clean
    if make_dir:
        oldCwd = os.getcwd()
        os.chdir(make_dir)
    if os.system(make) != 0:
        raise TestError('Failed to make')
    os.system(clean)
    if make_dir:
        os.chdir(oldCwd)
    # strip
    stripccCmd = stripcc
    if make != 'make':
        stripccCmd += ' -c "%s"' % make
    if make_dir:
        stripccCmd += ' -m "%s"' % make_dir
    # always in fast mode
    stripccCmd += ' -f'
    if os.system('%s >& %s/stripcc.out' % (stripccCmd, packageDir)) != 0:
        raise StripccError('Failed to strip')
    # check
    if make_dir:
        os.chdir(make_dir)
    os.system(clean)
    if os.system(make) != 0:
        raise StripccError('Failed to make')
    if make_dir:
        os.chdir(oldCwd)
    # get totalCode after strip
    return totalCode('.') * 100.0 / codeAmount

def main():
    # get stripcc's path
    oldCwd = os.getcwd()
    stripcc = oldCwd.rpartition('/')[0] + '/stripcc'
    if not os.path.exists(stripcc):
        print 'Can\'t find stripcc.'
        return

    # init logging system
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s [%(levelname)s]: %(message)s',
                        filename='./autotest.log',
                        filemode='a')
    logging.info('New test begin')

    # for each package
    entries = os.listdir('.')
    for entry in entries:
        if os.path.exists('%s/script' % entry):
            try:
                os.chdir(entry)
                remain = test(stripcc)
                os.chdir(oldCwd)
            except StripccError:
                logging.error('Failed to strip package: %s' % entry)
                os.chdir(oldCwd)
                continue
            except Exception, e:
                logging.error('Error on package: %s, %s' % (entry, str(e)))
                os.chdir(oldCwd)
                continue
            # strip OK
            logging.info('Stripped OK on %s, Remained/Original code: %f%%.' % (entry, remain))
            # get invalid source file if found 
            fp = open('%s/stripcc.out' % entry)
            for line in fp:
                m = re.search(r'Invalid source file: ([^,])+, ignore it', line)
                if m:
                    logging.info('Invalid source file: %s' % m.group(1))
            fp.close()

if __name__ == '__main__':
    main()
