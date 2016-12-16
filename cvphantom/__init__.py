from numpy import ones,zeros,linspace,radians,sin,arange,iinfo,tile,clip
from numpy.random import rand
from scipy.ndimage.filters import gaussian_filter,gaussian_laplace
from scipy.ndimage.interpolation import rotate,affine_transform
from scipy.ndimage import shift

def phantomTexture(U:dict):
    nrow,ncol = U['rowcol']
    fwidth = U['fwidth']
    dtype = U['dtype']

    bgmax = valmax(U['dtype'])
    bstep = round(bgmax/(nrow/2))
    rmax = bgmax

    texture = U['texture'].lower()

    if texture == 'wall':
        bg = bgmax * ones(U['rowcol'],dtype)
    elif texture == 'uniformrandom':
        bg = (bgmax * rand(U['rowcol'])).astype(dtype)
    elif texture == 'gaussian':
        bg = zeros(U['rowcol'],float)
        bg[nrow//2,ncol//2] = 1.
        bg = gaussian_filter(bg,U['gausssigma'])
        bg = bgmax * bg / bg.max()# normalize to full bit range
        bg = bg.astype(dtype)
        assert bg[nrow//2,ncol//2] == bgmax,'did you wrap value?'
    elif texture == 'vertsine':
        bgr = zeros(ncol,float) #yes, double to avoid quantization
        bg = zeros(U['rowcol'],dtype)
        bgr[ncol//2-fwidth//2:ncol//2+fwidth//2+1] = sin(radians(linspace(0,180,fwidth))) #don't do int8 yet or you'll quantize it to zero!
        rowind = range(nrow//4,nrow*3//4)
        bg[rowind,:] = bgmax * bgr
        bg = bg.astype(dtype) # needs to be its own line
    elif texture == 'laplacian':
        bg = zeros(U['rowcol'],float)
        bg[nrow//2,ncol//2] = 1.
        bg = -gaussian_laplace(bg,U['gausssigma'])
        bg -= bg.min()
        bg = bgmax * bg / bg.max() # normalize to full bit range
    elif texture == 'xtriangle':
        bg = zeros(ncol,dtype)
        bg[:ncol//2] = arange(0,rmax, bstep, dtype)
        bg[ncol//2:] = bg[:ncol//2][::-1]
        bg = tile(bg[None,:],[nrow,1]);
    elif texture == 'ytriangle':
        bg = zeros(nrow,dtype)
        bg[:nrow//2] = arange(0,rmax, bstep, dtype)
        bg[nrow//2:] = bg[:nrow//2][::-1]
        bg = tile(bg[:,None],[1,ncol])
    elif texture in ('pyramid','pyramid45'):
        bg = zeros(U['rowcol'],dtype)
        temp = arange(0, rmax, bstep, dtype)
        for i in range(1,nrow//2):
           bg[i,i:-i] = temp[i] #north face
           bg[i:-i,i] = temp[i] #west face
           bg[-i-1,i:-i] = temp[i] #south face
           bg[i:-i,-i-1] = temp[i] #east face

        if U['texture']=='pyramid45':
            bg = rotate(bg,45,reshape=False)
    elif texture == 'spokes': #3 pixels wide
        bg = zeros(U['rowcol']) # float to avoid overflow
        bg[nrow//2-fwidth//2:nrow//2 + fwidth//2, :ncol] = bgmax   #horizontal line
        bg[:nrow, ncol//2 - fwidth//2:ncol//2 + fwidth//2] = bgmax #vertical line
        bg = clip(bg + rotate(bg,45,reshape=False),0,bgmax).astype(dtype) #diagonal line
    elif texture== 'vertbar': #vertical bar, starts center of image
        bg = zeros(U['rowcol'],dtype)

        #bg(1:nRow,end-4:end) = bgMaxVal; %vertical line, top to bottom

        # vertical bar starts 1/4 from bottom and 1/4 from top of image
        bg[nrow*1//4:nrow*3//4, ncol//2 - fwidth//2:ncol//2 + fwidth//2] = bgmax
    else:
        raise TypeError('unspecified texture {} selected'.format(U['texture']))

    return bg

def valmax(dtype):
    try:
        bgmax = iinfo(dtype).max
    except ValueError:
        if dtype is float:
            bgmax = 1. #normalize
        else:
            raise ValueError('unknown dtype {}'.format(dtype))

    print('max pixel intensities for {} are taken to be: {}'.format(dtype,bgmax))

    return bgmax


def translateTexture(bg,U:dict):
# function data = translateTexture(bg,data,swirlParam,U)
# to make multiple simultaneous phantoms, call this function repeatedly and sum the result

    if not 'motion' in U:
        U['motion']=None
    if not 'nframe' in U:
        U['nframe']=1
    if not 'fstep' in U or not U['fstep']:
        U['fstep']=1

    nrow,ncol = U['rowcol']
    nframe = U['nframe']
    data = zeros((nframe,nrow,ncol), bg.dtype) #initialize all frame

#    try:
#        swx0 = swirlParam.x0; swy0 = swirlParam.y0;
#        swstr = swirlParam.strength; swrad = swirlParam.radius;
#%% indices for frame looping
    I = range(0,nframe,U['fstep'])

    if isinstance(U['motion'],str):
        motion = U['motion'].lower()
    else:
        motion = U['motion']

    if motion in (None,'none'):
        for i in I:
            data[i,...] = bg
#    elif motion == 'swirlstill': #currently, swirl starts off weak, and increases in strength
#        swirlParam.x0(1:length(swirlParam.x0)) = U.fwidth; #FIXME
#        print('The Swirl algorithm is alpha-testing--needs manual positioning help--try vertbar texture')
#        for i in range(I):
#           data[i,...] = makeSwirl(bg,...
#                                 swx0,swy0,...
#                                 swstr * (i-1), swrad,...
#                                 false,fillValue,U.bitdepth);
#    elif motion == 'shearrightswirl':
#        print('swirl location not matching shear right now? shear going wrong way?')
#        swx0(1:length(swy0)) = U.fwidth; %FIXME
#        # swirl, then shear
#        for i in range(I):
#
#            #Step 1: swirl
#            dataFrame = makeSwirl(bg,...
#                                 swx0,swy0,...
#                                 swstr * (i-1), swrad,...
#                                 false,fillValue,U.bitdepth);
#            #step 2: shear
#            data[i,...] = doShearRight(dataFrame,RA,i,nFrame,U.dxy(1),U.rowcol,fillValue);
    elif motion == 'rotate360ccw':
        for i in I:
            q = (nframe-i)/nframe*360 #degrees
            data[i,...] = rotate(bg,q,reshape=False)
    elif motion == 'rotate180ccw':
        for i in I:
            q = (nframe-i)/nframe*180 #degrees
            data[i,...] = rotate(bg,q,reshape=False)
    elif motion == 'rotate90ccw':
        for i in I:
            q = (nframe-i)/nframe*90 #degrees
            data[i,...] = rotate(bg,q,reshape=False)
    elif motion == 'shearright':
        for i in I:
            data[i,...] = doShearRight(bg,i,U)
    elif motion == 'diagslide':
        for i in I:
            data[i,...] = shift(bg, [-nframe+i*U.dxy[1], -nframe+i*U.dxy[0]])
    elif motion == 'horizslide':
        print('Horizontally moving feature, dim: {}'.format(data.shape))
        for i in I:
            data[i,...] = shift(bg, [0,-nframe+i*U['dxy'][0]])
    elif motion == 'vertslide':
        for i in I:
            data[i,...] = shift(bg, [-nframe+i*U['dxy'][1],0])
    else:
        ValueError('Unknown motion method {}'.format(U['translate']))

    return data

def doShearRight(bg,i,U):
    nframe = U['nframe']

    T = [[1,0,0],
         [(nframe-i*U['dxy'][0])/nframe,1,0],
         [0,0,1]]

    return affine_transform(bg,T)
