def find_flag_blocks(flag,count=False):

    """Copied from find_blocks function in Cyrille's glitchtools.py.
    Find the blocks of adjacent flagged points and return first point of each zone
    (and optionally the number of points in the block)."""

    marks = flag[1:]*1-flag[:-1]
    start = nm.where(marks == 1)[0]+1
    if flag[0]:
        start = nm.concatenate([[0],start])
    if count:
        end = nm.where(marks == -1)[0]
        if flag[-1]:
            end = nm.concatenate([end,[len(flag)-1]])
        n = end-start+1
        return start,n
    else:
        return start
        

def expandflag(flag, before=5, after=5):

    """Expand flagged samples to include specified number of before/after samples.
    Modified from rosset's extflag function in glitchtools.py.

    - flag: flag field
    - before: # of samples to flag before each flagged point
    - after: # of samples to flag after each flagged point

    Returns expanded flag field."""

    inds = nm.where(nm.asarray(flag) > 0)[0]
    flag2 = nm.asarray(flag).copy()
    for i in inds:
        flag2[max(i-before,0):min(i+after+1,flag2.size)] = 1
    return flag2
