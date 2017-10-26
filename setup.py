from setuptools import setup, find_packages

setup(
    name='galera_start',
    version='1.0',
    url='https://github.com/fengbao123/galera_start',
    license='',
    author='fengbao',
    author_email='b1f2@vip.qq.com',
    description='test',

    packages = find_packages(),

    data_files = [('/usr/share/my_modules/', ['src/ansible_modules/get_galera_info.py','src/ansible_modules/set_safe_to_bootstrap.py'])],
    scripts = ['scripts/galera_start.py'],

    install_requires=[
        'ansible>=2.2'
    ]
)