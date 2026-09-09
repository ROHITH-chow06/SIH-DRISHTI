import math

def generate_curve(start, end, control_points, num_points):
    # simple bezier or just spline
    # let's just do a simple bezier for 1 control point (quadratic)
    pass

# We can just manually define a zig-zag realistic looking mountain road
# Mountain roads have switchbacks.

points_main = [
    (18.6700, 81.1850),
    (18.6710, 81.1855),
    (18.6725, 81.1865),
    (18.6740, 81.1870),
    (18.6750, 81.1880),
    (18.6755, 81.1895),
    (18.6765, 81.1905),
    (18.6780, 81.1915),
    (18.6795, 81.1925),
    (18.6805, 81.1920), # switchback
    (18.6815, 81.1930),
    (18.682072, 81.193572), # anchor
    (18.6830, 81.1945),
    (18.6845, 81.1950),
    (18.6860, 81.1955),
    (18.6875, 81.1965),
    (18.6885, 81.1975),
    (18.6900, 81.1985),
    (18.6920, 81.1995),
    (18.6940, 81.2010),
    (18.6960, 81.2030),
]

points_sec = [
    (18.682072, 81.193572),
    (18.6825, 81.1920),
    (18.6835, 81.1900),
    (18.6830, 81.1885),
    (18.6820, 81.1870),
    (18.6805, 81.1850),
    (18.6790, 81.1830),
    (18.6775, 81.1810),
    (18.6760, 81.1800),
]

points_loop = [
    (18.6760, 81.1800),
    (18.6750, 81.1810),
    (18.6735, 81.1830),
    (18.6720, 81.1855),
    (18.6710, 81.1855), # joins back to main
]

def format_points(points):
    return "[\n" + ",\n".join(f"                    Position(latitude={p[0]}, longitude={p[1]})" for p in points) + "\n                ]"

print(f"MAIN: {format_points(points_main)}")
print(f"SEC: {format_points(points_sec)}")
print(f"LOOP: {format_points(points_loop)}")
