A='23456789CFGHJMPQRVWX'
SEP_POS=8
def encode(lat,lon,length=11):
    # clip / normalize
    if lat < -90: lat=-90
    if lat > 90: lat=90
    lon=(lon+180)%360-180
    if lat==90: lat=90-1e-10
    code=''
    # first 10 chars: pairs
    latv=int(round((lat+90)*2.5e7))
    lonv=int(round((lon+180)*8.192e6))
    # grid refinement part (chars 11+)
    grid=''
    lv,ov=latv,lonv
    for i in range(5):
        grid = A[(lv%5)*4+(ov%4)] + grid
        lv//=5; ov//=4
    # pair part
    pair=''
    for i in range(5):
        pair = A[lv%20] + A[ov%20] + pair
        lv//=20; ov//=20
    code = pair[:SEP_POS] + '+' + pair[SEP_POS:] + grid
    return code[:length+1] if length>=SEP_POS else code

def short(full, n=7):
    # the "XXXX+XX" local form Google shows with a locality
    return full[4:4+n]

lat,lon=36.0675472,-115.1779391
full=encode(lat,lon,11)
print("full  :",full)
print("10-dig:",encode(lat,lon,10))
print("local :",short(encode(lat,lon,10)))
