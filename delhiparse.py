#!/usr/bin/python3
import os,sys,bs4,datetime

def parse(vent=False):
    if os.path.exists('tmp.htm'):os.remove('tmp.htm')
    website='https://delhifightscorona.in/data/non-covid-icu-beds/'
    if vent: website='https://delhifightscorona.in/data/ventilators/'
    cmd='wget -q "'+website+'" -O tmp.htm';y=os.popen(cmd).read()
    soup=bs4.BeautifulSoup(open('tmp.htm'))
    x=soup('div',attrs={'class':'callout'})
    total=int(x[0]('h1')[0].text)
    occupied=int(x[1]('h1')[0].text)
    vacant=int(x[2]('h1')[0].text)
    date=datetime.datetime.now().strftime('%d-%m')
    btype='non-covid icu'
    if vent: btype='ventilators' 
    print('In Delhi, on date: %s, %s beds:\ntotal: %d\noccupied: %d\nvacant: %d' %(date,btype,total,occupied,vacant))
    os.remove('tmp.htm')
if __name__=='__main__':
    parse()
    parse(vent=True)
