from scipy.misc import bytescale
from matplotlib.pyplot import figure,draw, pause
#
try:
    from pyimagevideo.writeavi_opencv import videoWriter
except ImportError:
    videoWriter=None

def playwrite(imgs,fmt,texture,motion,nframe):
    fg = figure()
    ax=fg.gca()
    hi = ax.imshow(imgs[...,0])
    fg.colorbar(hi)

    if fmt == 'avi' and videoWriter is not None: #output video requested
        ofn = '{}_{}.avi'.format(texture, motion)
        print('writing {}'.format(ofn))
        hv = videoWriter(ofn,'FFV1',imgs.shape[:2][::-1],usecolor=False)
    elif fmt is not None:
        from skimage import io
        io.use_plugin('freeimage')
        hv = fmt
    else:
        hv = None


    for i in range(nframe):
        hi.set_data(imgs[...,i])
        ax.set_title('{}'.format(i))
        draw(), pause(0.02)
        if hv is not None:
            if isinstance(hv,str):
                ofn = '{}_{}_{}.{}'.format(texture, motion,i,hv)
                print('writing {}'.format(ofn))
                io.imsave(ofn,imgs[...,i])
            else:
                hv.write(bytescale(imgs[...,i],cmin=0,cmax=imgs.max()))

    try:
        hv.release()
    except AttributeError:
        pass
