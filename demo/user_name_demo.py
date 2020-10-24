from schalter import Schalter

Schalter["user_name"] = "James"


@Schalter.configure(name="user_name")
def print_msg(*, name):
    print("Hello {}".format(name))


print_msg()
