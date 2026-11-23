def interp(current,prevmm,prevv,folmm,folv):
    return float(prevmm+(current-prevv)*(folmm-prevmm)/(folv-prevv))

def calInterp(v,iCald,iCalv):
    if v<=iCalv[0]:
        return float(iCald[0])
    if v>iCalv[len(iCalv)-1]:
        return float(iCald[len(iCald)-1])
    for i in range(len(iCald)-1):
        if v<iCalv[i+1]:
            return interp(v,iCald[i],iCalv[i],iCald[i+1],iCalv[i+1])
    return float(iCald[len(iCald)-1])

def calib(v,iCalib):
    C=iCalib.split('_')
    if len(C) != 2:
        return -1.0
    cal_mm = [int(x) for x in C[0].split('-')]
    cal_v = [int(x) for x in C[1].split('-')]
    return calInterp(v,cal_mm,cal_v)
    
