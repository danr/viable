
from microlib import x as microlib_x

print('minilib pre:', globals().get('x'), microlib_x)
x = 1
print('minilib post:', globals().get('x'), microlib_x)

