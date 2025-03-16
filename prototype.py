from PIL import Image

# Create a new 20x20 image with transparency
img = Image.new('RGBA', (20, 20), (0, 0, 0, 0))
pixels = img.load()

# Define colors
BROWN_OUTLINE = (139, 69, 19, 255)  # Dark brown for outline
LIGHT_BROWN = (165, 42, 42, 255)    # Light brown for fill
DARK_BROWN = (101, 67, 33, 255)     # Dark brown for planks
SHADOW = (80, 50, 20, 255)          # Darker brown for shadow

# Draw the crate
for x in range(20):
    for y in range(20):
        # Outline
        if x == 0 or x == 19 or y == 0 or y == 19:
            pixels[x, y] = BROWN_OUTLINE
        # Fill with light brown
        else:
            pixels[x, y] = LIGHT_BROWN

# Add planks (diagonal lines)
for i in range(3, 6):
    pixels[i, i] = DARK_BROWN
    pixels[i + 1, i] = DARK_BROWN
for i in range(7, 10):
    pixels[i, i] = DARK_BROWN
    pixels[i + 1, i] = DARK_BROWN

# Add shadow in bottom-right corner
for x in range(16, 20):
    for y in range(16, 20):
        pixels[x, y] = SHADOW

# Save the image
img.save("assets/crate2.png", "PNG")
print("crate2.png has been created and saved in the 'assets' folder.")