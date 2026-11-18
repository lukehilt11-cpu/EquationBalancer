from PIL import Image, ImageDraw, ImageFont
import glob

def find_font(size):
    for p in glob.glob('/usr/share/fonts/**/*Bold*.ttf', recursive=True) + glob.glob('/usr/share/fonts/**/*.ttf', recursive=True):
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            pass
    return ImageFont.load_default()

S = 1024
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
# rounded square background
d.rounded_rectangle((40, 40, S-40, S-40), radius=200, fill=(30, 90, 160, 255))
# balance scale: beam, pivot, pans
white = (255, 255, 255, 255)
d.polygon([(512, 330), (440, 620), (584, 620)], fill=white)          # fulcrum
d.rounded_rectangle((200, 300, 824, 340), radius=20, fill=white)      # beam
for cx in (240, 784):
    d.line((cx, 320, cx-90, 560), fill=white, width=14)
    d.line((cx, 320, cx+90, 560), fill=white, width=14)
    d.chord((cx-130, 480, cx+130, 640), 0, 180, fill=white)
d.rounded_rectangle((330, 640, 694, 680), radius=20, fill=white)      # base
# text
f = find_font(230)
txt = "A+B"
w = d.textlength(txt, font=f)
d.text(((S-w)/2, 720), txt, font=f, fill=white)

img.save("icon_1024.png")
img.save("icon.ico", sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
img.save("icon.icns")
print("ok")
