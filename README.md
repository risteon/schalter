# schalter

[![Build Status](https://travis-ci.org/risteon/schalter.svg?branch=master)](https://travis-ci.org/risteon/schalter)


The main feature of this package is to provide a decorator that records
keyword-only function arguments into a configuration and allows to
re-instantiate the values later (e.g. from a configuration file). See this MWE:

``` python
from schalter import Schalter


@Schalter.configure
def decorate_cake(cake, *, glaze="butter_cream", number_of_sprinkes: int = 10):
    cake.glaze(glaze)
    cake.sprinkle(number_of_sprinkes)


print("Glaze:", Schalter["glaze"])
print("Sprinkles:", Schalter["number_of_sprinkes"])
```
This outputs:
```
Glaze: butter_cream
Sprinkles: 10
```


You can also track an individual keyword-only argument under another configuration key:

``` python
from schalter import Schalter

Schalter["user_name"] = "James"


@Schalter.configure(name="user_name")
def print_msg(*, name):
    print("Hello {}".format(name))


print_msg()
```

Output:
```
Hello James
```