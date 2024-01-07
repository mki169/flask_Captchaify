from setuptools import setup, find_packages
from pip._internal.req import parse_requirements

requirements = [str(requirement.requirement) for requirement in list(parse_requirements("requirements.txt", session=False))]

with open('README.md', 'r', encoding='utf-8') as readable_file:
    long_description = readable_file.read()

long_description = long_description.split("</picture>")[1]
long_description = '[![Picture from Block Page](https://github.com/tn3w/flask_Captchaify/releases/download/v0.3/blocked-dark.png)](https://github.com/tn3w/flask_Captchaify)' + long_description

setup(
    name='flask_Captchaify',
    version='1.3.4',
    description='Protect against bots and DDoS attacks',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='TN3W',
    author_email='tn3wA8xxfuVMs2@proton.me',
    url='https://github.com/tn3w/flask_Captchaify',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    package_data={
        'flask_Captchaify': ['data/*', 'templates/*']
    },
    classifiers=[
        'Environment :: Web Environment',
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
    license='GPL-3.0',
    keywords='flask, Python, Bot, Captcha, DDoS',
    install_requires=requirements
)
