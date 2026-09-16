from pathlib import Path
from PIL import Image, ImageDraw
BG='#0a120d'; A='#65e49a'; B='#a7f0c3'
def rgb(h):
    h=h.lstrip('#'); return tuple(int(h[i:i+2],16) for i in (0,2,4))+(255,)
img=Image.new("RGBA",(256,256),rgb(BG)); d=ImageDraw.Draw(img); A=rgb(A); B=rgb(B)
d.rounded_rectangle((50,50,146,122),16,fill=(24,48,34,255),outline=A,width=10); d.rounded_rectangle((84,86,206,174),18,fill=(16,35,25,255),outline=B,width=10); d.line((76,196,180,196),fill=A,width=12); d.line((96,174,106,196),fill=A,width=12); d.line((160,174,150,196),fill=A,width=12)
out=Path(__file__).resolve().parents[1]/"assets"/"icon.ico"
out.parent.mkdir(exist_ok=True)
img.save(out,format="ICO",sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
print(out)