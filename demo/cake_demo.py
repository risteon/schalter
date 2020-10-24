from schalter import Schalter


@Schalter.configure
def decorate_cake(cake, *, glaze="butter_cream", number_of_sprinkes: int = 10):
    cake.glaze(glaze)
    cake.sprinkle(number_of_sprinkes)


print("Glaze:", Schalter["glaze"])
print("Sprinkles:", Schalter["number_of_sprinkes"])
