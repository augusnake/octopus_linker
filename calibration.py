def interp(current,prevmm,prevv,folmm,folv):
    return float(prevmm+(current-prevv)*(folmm-prevmm)/(folv-prevv))

def calInterp(v,cald,calv):
    if v<=calv[0]:
        return float(cald[0])
    if v>calv[len(calv)-1]:
        return float(cald[len(cald)-1])
    for i in range(len(cald)-1):
        if v<calv[i+1]:
            return interp(v,cald[i],calv[i],cald[i+1],calv[i+1])
    return float(cald[len(cald)-1])

def calib(v,calib):
    C=calib.split('_')
    if len(C) != 2:
        return 0.0
    cal_mm = [int(x) for x in C[0].split('-')]
    cal_v = [int(x) for x in C[1].split('-')]
    return calInterp(v,cal_mm,cal_v)
    