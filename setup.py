from setuptools import setup

test_deps = [
    'pytest',
    'pytest-cov',
]
extras = {
    'test': test_deps,
}

setup(name='schalter',
      version='0.3alpha0',
      description='Fast and simple configuration',
      url='http://github.com/risteon/schalter',
      author='Christoph Rist',
      author_email='c.rist@posteo.de',
      license='Apache-2.0',
      packages=['schalter'],
      zip_safe=False,
      install_requires=[
          'decorator',
          'ruamel.yaml',
      ],
      setup_requires=['pytest-runner'],
      tests_require=test_deps,
      extras_require=extras,
      python_requires='>=3.6',
      classifiers=[
          'Development Status :: 3 - Alpha',
          'Intended Audience :: Developers',
      ],
      )
