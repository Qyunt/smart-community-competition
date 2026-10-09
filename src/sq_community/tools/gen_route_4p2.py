#!/usr/bin/env python3
"""Directed centre-line route following the blue arrows in rules page 3."""
from collections import deque
import csv
import math
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]

def edges(node):
    x,y=node
    out=[]
    if y==19 and 1<x<=19:out.append((x-1,y))
    if x==1 and 1<y<=19:out.append((x,y-1))
    if y==13 and 1<=x<10:out.append((x+1,y))
    if x==10 and 1<y<=13:out.append((x,y-1))
    if y==1 and 1<=x<16:out.append((x+1,y))
    if x==16 and 1<=y<19:out.append((x,y+1))
    return out

def shortest_path(start,goal):
    queue=deque([start]);prev={start:None}
    while queue:
        here=queue.popleft()
        if here==goal:break
        for nxt in edges(here):
            if nxt not in prev:prev[nxt]=here;queue.append(nxt)
    if goal not in prev:raise ValueError('Unreachable directed goal: %s -> %s'%(start,goal))
    path=[];here=goal
    while here is not None:path.append(here);here=prev[here]
    return path[::-1]

def world(index):return -2+.2*index

def main():
    with (PKG/'route/task_points_4p2.csv').open(encoding='utf-8-sig',newline='') as f:tasks=list(csv.DictReader(f))
    current=(19,19);rows=[];counter=0;last_task=''
    for task in tasks:
        goal=(int(task['grid_x']),int(task['grid_y']))
        # Finish access goes east within the upper-right entrance, after leaving the east lane.
        path=shortest_path(current,(16,19)) + [(17,19),(18,19),(19,19)] if task['task_id']=='RETURN' else shortest_path(current,goal)
        selected=set()
        for i in range(1,len(path)-1):
            incoming=(path[i][0]-path[i-1][0],path[i][1]-path[i-1][1])
            outgoing=(path[i+1][0]-path[i][0],path[i+1][1]-path[i][1])
            if incoming!=outgoing:selected.add(i)
            # A checkpoint beyond each bar guarantees the body clears it before later turns.
            if last_task.startswith('TL_UP_WAIT') and path[i]==(10,19):selected.add(i)
            if last_task=='TL_LOW_WAIT' and path[i]==(10,4):selected.add(i)
        for i in sorted(selected):
            counter+=1;x,y=path[i];nx,ny=path[i+1]
            rows.append(('过路%02d'%counter,world(x),world(y),math.atan2(ny-y,nx-x),''))
        rows.append((task['task_id'],world(goal[0]),world(goal[1]),float(task['yaw_rad']),'观察并保存图像' if task['task_id']!='RETURN' else '返回终点'))
        current=goal;last_task=task['task_id']
    with (PKG/'route/sq_route_patrol_4p2.csv').open('w',encoding='utf-8',newline='') as f:
        f.write('# Directed engineering route from rules p3; runtime acceptance is recorded separately.\n')
        writer=csv.writer(f,lineterminator='\n');writer.writerow(('名称','x','y','yaw','播报'))
        for name,x,y,yaw,msg in rows:writer.writerow((name,'%.3f'%x,'%.3f'%y,'%.5f'%yaw,msg))
    print('Route:',len(tasks),'observation tasks;',counter,'turn/clearance goals;',len(rows),'total')

if __name__=='__main__':main()
