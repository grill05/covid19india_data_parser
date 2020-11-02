#!/usr/bin/python3
import os,sys,bs4

def parse(vent=False):
    if os.path.exists('tmp.htm'):os.remove('tmp.htm')
    website='https://delhifightscorona.in/data/non-covid-icu-beds/'
    if vent: website='https://delhifightscorona.in/data/ventilators/'
    cmd='wget "'+website+'" -O tmp.htm';os.system(cmd)
    soup=bs4.BeautifulSoup(open('tmp.htm'))
    x=soup('div',attrs={'class':'callout'})
    total=int(x[0]('h1')[0].text)
    occupied=int(x[1]('h1')[0].text)
    vacant=int(x[2]('h1')[0].text)
    date=datetime.datetime.now().strftime('%d-%m')
    print('In Delhi, on date: %s, non-covid icu beds:\ntotal: %d\noccupied: %d\nvacant: %d' %(date,total,occupied,vacant))
    os.remove('tmp.htm')
if __name__=='__main__':
    parse()
    parse(vent=True)
