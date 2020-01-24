from setuptools import setup

setup(name='schalter',
      version='0.1.0.dev1',
      description='Fast and simple configuration',
      url='http://github.com/risteon/schalter',
      author='Christoph Rist',
      author_email='c.rist@posteo.de',
      license='Apache-2.0',
      packages=['schalter'],
      zip_safe=False,
      install_requires=[
          'ruamel.yaml',
      ],
      setup_requires=['pytest-runner'],
      tests_require=['pytest'],
      python_requires='>=3.6',
      classifiers=[
          'Development Status :: 3 - Alpha',
          'Intended Audience :: Developers',
      ],
      )
