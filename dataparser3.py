#!/usr/bin/python2

#code runs with python-2 (for python-3, just convert the "print" statements to function
#to install dependencies "pip install pylab json requests"

# ~ for moving average with window 'N'
# ~ np.convolve(x, np.ones((N,))/N, mode='valid')

import os,sys,copy,tqdm,csv,lazy_import


pylab=lazy_import.lazy_module('pylab')
requests=lazy_import.lazy_module('requests')
np=lazy_import.lazy_module('numpy')
pd=lazy_import.lazy_module('pandas')
numpy=np
colorama=lazy_import.lazy_module('colorama')
mdates=lazy_import.lazy_module('matplotlib.dates')
BASEDIR=os.path.abspath('.').split('covid19india_data_parser')[0]+'covid19india_data_parser/'

import json,datetime
# ~ import matplotlib.dates as mdates
# ~ import numpy as np
datetime_doa_marker=datetime.datetime(2020, 1, 1, 0, 0)

TMPDIR='/storage/emulated/0/code/covid19india_data_parser/ims/tmp/'
if  'ani' in os.uname()[1] : TMPDIR='/home/ani/code/covid19india_data_parser/ims/'
state_code_to_name={"an" : "Andaman and Nicobar Islands" ,"ap" : "Andhra Pradesh" ,
                    "ar" : "Arunachal Pradesh" ,"as" : "Assam" ,
                    "br" : "Bihar" ,"ch" : "Chandigarh" ,
                    "ct" : "Chhattisgarh" ,"dn" : "Dadra and Nagar Haveli and Daman and Diu" ,
                    "dl" : "Delhi" ,"ga" : "Goa" ,
                    "gj" : "Gujarat" ,"hr" : "Haryana" ,
                    "hp" : "Himachal Pradesh" ,"jk" : "Jammu and Kashmir" ,
                    "jh" : "Jharkhand" ,"ka" : "Karnataka" ,
                    "kl" : "Kerala" ,"la" : "Ladakh" ,    
                    "ld" : "Lakshadweep" , "mp" : "Madhya Pradesh" ,
                    "mh" : "Maharashtra" , "mn" : "Manipur" ,
                    "ml" : "Meghalaya" , "mz" : "Mizoram" ,       
                    "nl" : "Nagaland" ,  "or" : "Odisha" ,
                    "py" : "Puducherry" ,"pb" : "Punjab" ,    
                    "rj" : "Rajasthan" , "sk" : "Sikkim" ,                                  
                    "un" : "State Unassigned" ,"tn" : "Tamil Nadu" ,
                    "tg" : "Telangana" , "tr" : "Tripura" ,
                    "up" : "Uttar Pradesh" ,   "ut" : "Uttarakhand" ,      
                    "wb" : "West Bengal" , 'jk': 'Jammu and Kashmir'
                    }
state_name_to_code={}
for k in state_code_to_name: state_name_to_code[state_code_to_name[k]]=k

#bengaluru-urban and bengaluru-rural taken together as one for our purposes
karnataka_districts_map={'bagal':'bagalkote','balla':'ballari','chikkam':'chikkamagaluru',
  'belag':'belagavi','benga':'bengaluru','bida':'bidar','chamaraj':'chamarajanagara','chikkab':'chikkaballapura',
  'chitra':'chitradurga','dakshin':'dakshinkannada','davan':'davangere',
  'dhar':'dharwada','gada':'gadag','hass':'hassan','have':'haveri','kala':'kalaburagi',
  'koda':'kodagu','kola':'kolara','kopp':'koppala','mand':'mandya','mysu':'mysuru','raich':'raichuru',
  'raman':'ramanagara','shiva':'shivamogga','tuma':'tumakuru','udup':'udupi','uttar':'uttarakannada',
  'vija':'vijayapura','yadag':'yadagiri'};

pop_growth_multiples={'Chhattisgarh': 1.15, 'Karnataka': 1.15,'Tamil Nadu': 1.07,
                      'Kerala': 1.043,'Delhi': 1.23,'Maharashtra':1.114,'Uttar Pradesh':1.201,
                      'Rajasthan': 1.207,'Gujarat': 1.19,'West Bengal': 1.06,'Punjab': 1.11}
def parse_census_district(state='Karnataka',district='Bengaluru Urban',metric='urban'):
    import csv;r=csv.reader(open('india-districts-census-2011.csv'));info=[]
    for i in r :info.append(i)
    info=[i for i in info if i[1]==state.upper()]
    info=[i for i in info if i[2]==district]
    if not info:
        print('data for district: %s not found in census file' %(district))
        return
    info=info[0]
    if metric in ['urban','urbanization']:
        ruralh=info[37]
        urbanh=info[38]
        toth=info[39]
        urbanization=100*(float(urbanh)/int(toth))
        return urbanization

    return info
def vaccination_state(state='Delhi',mohfw=True,check=False):
  if len(state)==2 and state in state_code_to_name: x=state;state=state_code_to_name[state];
  if mohfw:
    r=csv.reader(open('vaccine_doses_statewise.csv'))
    info=[]
    for i in r: info.append(i)
    dates=[datetime.datetime.strptime(i,'%d/%m/%Y') for i in info[0][1:]]
    info=info[1:]
    info=[i[1:] for i in info if i[0]==state]
    # ~ print(info[0])
    # ~ return info[0]    
    
    if info:
      #fix empty point
      info=info[0]
      xx=[];last=info[0]
      for i in info:
        if i: xx.append(i);last=i
        else: xx.append(last)
      
      # ~ try:
      info=list(np.int_(xx))
      #add interpolated data for 17Feb
      dates.insert(1,datetime.datetime(2021, 1, 17, 0, 0))
      info.insert(1,int((info[0]+info[1])/2))
      # ~ except:
      
        # ~ print('int conversion failed for '+str(info[0]))
      info2=[info[0]]
      info2.extend(np.diff(info))
      return list(zip(dates,info2,info))
    else:
      return

  r=csv.reader(open('statewise_tested_numbers_data.csv'))
  info=[]
  for i in r: info.append(i)
  info=info[1:]
  info2=[]

  if check:
    hasdoses=set();hasdosessess=set()
    for i in info:
      if len(i)<16: continue
      cstate=i[1];date=i[0]
      date=datetime.datetime.strptime(date,'%d/%m/%Y')
      cumdoses=i[10];cumsess=i[11];cumaefi=i[12]
      if cumdoses:
        #print(i)
        if cumsess: hasdosessess.add(cstate)
        else: hasdoses.add(cstate)
    print('States with only doses:\n\t%s\nStates with doses and sessions:\n\t%s' %(str(list(set(hasdoses))),str(list(set(hasdosessess)))) )
    return 

  for i in info:
    if len(i)<16: continue
    cstate=i[1];date=i[0]
    date=datetime.datetime.strptime(date,'%d/%m/%Y')
    cumdoses=i[10];cumsess=i[11];cumaefi=i[12]
    cumcs=i[13];cumcx=i[14]
    if cumdoses or cumsess: # or cumaefi or cumcs or cumcx:
      if not (int(cumdoses) or int(cumsess)): continue
      if state:
        if cstate!=state: continue
        info2.append((date,cumdoses,cumsess)) #,cumaefi,cumcs,cumcx))
      else:
        info2.append((date,cstate,cumdoses,cumsess)) #,cumaefi,cumcs,cumcx))

  info=[];
  #print(info2)
  
  dt,d,s=info2[0][0],info2[0][1],info2[0][2]
  if d: d=int(d)
  if s: s=int(s)
  info.append((dt,d,s,float(d)/s))

  for j in range(len(info2[1:])):
    pd=int(info2[j][1]);ps=info2[j][2]
    if not ps: ps=0
    else: ps=int(ps)

    cd=int(info2[j+1][1]);cs=info2[j+1][2]
    if cs: cs=int(cs)
    else: cs=0

    dd=cd-pd;ds=cs-ps;dps=0
    if not (dd or ds): continue
    if dd and ds: dps=float(dd)/ds
    
    info.append((info2[j+1][0],dd,ds,dps))
 

  if not state:  return info2
  #else: return info,info2
  else: return info

def diffdata(data):  
  data2=[data[0]];  data2.extend(np.diff(data))
  return data2

# ~ def vaccination_national():
  # ~ r=csv.reader(open('tested_numbers_icmr_data.csv'))
  # ~ info=[]
  # ~ for i in r: info.append(i)
  # ~ info2=[]
  # ~ info0=info[1:]
  # ~ for i in info[1:]:
    # ~ date=i[1];#date=date.replace('/1/','/01/')
    # ~ cumreg=i[10]
    # ~ cumsessions=i[11]
    # ~ cumsites=i[12]
    # ~ cum1stdoses=i[13]
    # ~ cum2nddoses=i[14]
    # ~ cummales=i[15]
    # ~ cumfemales=i[16]
    # ~ cumcovaxin=i[18]
    # ~ cumcovidshield=i[19]
    # ~ cumind=i[20]
    # ~ cumdoses=i[21]
    
    # ~ if cumdoses or cumsessions:
      # ~ date=datetime.datetime.strptime(date,'%d/%m/%Y');prog=''
      
      # ~ if not cumreg: cumreg=0
      # ~ else: cumreg=int(cumreg)
      # ~ if not cumsessions: cumsessions=0
      # ~ else: cumsessions=int(cumsessions)
      # ~ if not cumsites: cumsites=0
      # ~ else: cumsites=int(cumsites)
      # ~ if not cum1stdoses: cum1stdoses=0
      # ~ else: cum1stdoses=int(cum1stdoses)
      # ~ if not cum2nddoses: cum2nddoses=0
      # ~ else: cum2nddoses=int(cum2nddoses)
      # ~ if not cummales: cummales=0
      # ~ else: cummales=int(cummales)
      # ~ if not cumfemales: cumfemales=0
      # ~ else: cumfemales=int(cumfemales)
      # ~ if not cumcovaxin: cumcovaxin=0
      # ~ else: cumcovaxin=int(cumcovaxin)
      # ~ if not cumcovidshield: cumcovidshield=0
      # ~ else: cumcovidshield=int(cumcovidshield)
      # ~ if not cumind: cumind=0
      # ~ else: cumind=int(cumind)
      # ~ if not cumdoses: cumdoses=0
      # ~ else: cumdoses=int(cumdoses)

        
      # ~ info2.append((date,cumreg,cumsessions,cumsites,cum1stdoses,cum2nddoses,cummales,cumfemales,cumcovaxin,cumcovidshield,cumind,cumdoses))

  # ~ info=[]

  
  # ~ dates,cumreg,cumsessions,cumsites,cum1stdoses,cum2nddoses,cummales,cumfemales,cumcovaxin,cumcovidshield,cumind,cumdoses=zip(*info2)
  
  # ~ cumreg=np.diff(cumreg);cumsessions=np.diff(cumsessions);cumsites=np.diff(cumsites);cum1stdoses=np.diff(cum1stdoses);cum2nddoses=np.diff(cum2nddoses);
  # ~ cummales=np.diff(cummales);cumfemales=np.diff(cumfemales);cumcovaxin=np.diff(cumcovaxin);cumcovidshield=np.diff(cumcovidshield);
  # ~ cumind=np.diff(cumind);cumdoses=np.diff(cumdoses);
  
  # ~ info.append(info2[0])
  
  # ~ for j in range(len(cumreg)):
    # ~ info.append((dates[j+1],cumreg[j],cumsessions[j],cumsites[j],cum1stdoses[j],cum2nddoses[j],cummales[j],cumfemales[j],cumcovaxin[j],cumcovidshield[j],cumind[j],cumdoses[j]))
  
  # ~ return info

def intz(string_int):
  if not string_int: return 0
  else: return int(string_int)
def vaccination_cowin_state(state='ka'):
  if len(state)==2 and state in state_code_to_name: x=state;state=state_code_to_name[state];
  x=csv.reader(open('cowin_vaccine_data_statewise.csv'));info=[]
  for i in x: info.append(i)
  data=[];zd={'':0}
  for i in info[1:]:
    # ~ try:
    date,sstate,tot_persons_vaccinated,tot_sessions,tot_sites,firstdoses,seconddoses,males,females,transgenders,covaxin,covishield,sputnik,sefi,from18to45,from45to60,over60,totdoses=i
    if sstate!=state: continue
    
    tot_persons_vaccinated=intz(tot_persons_vaccinated)
    tot_sessions=intz(tot_sessions)      
    firstdoses=intz(firstdoses)
    seconddoses=intz(seconddoses)
    females=intz(females)
    males=intz(males)
    covaxin=intz(covaxin)
    covishield=intz(covishield)
    sputnik=intz(sputnik)
    from18to45=intz(from18to45)
    from45to60=intz(from45to60)
    over60=intz(over60)
    totdoses=intz(totdoses)
    date=datetime.datetime.strptime(date,'%d/%m/%Y')
    data.append((date,tot_persons_vaccinated,tot_sessions,firstdoses,seconddoses,males,females,covaxin,covishield,sputnik,from18to45,from45to60,over60,totdoses))
    # ~ except:
      # ~ print('failed for '+str(i))
      # ~ return
  return data

def vaccination_national():
  x=json.load(open('national_data.json'))['tested']
  x=[i for i in x if 'firstdoseadministered' in i and i['firstdoseadministered']]
  firstdoses=[];seconddoses=[];dates=[]
  frontlinefirstdoses=[];frontlineseconddoses=[];hcwfirstdoses=[];hcwseconddoses=[]
  over60firstdoses=[];over60seconddoses=[];upto60firstdoses=[];upto60seconddoses=[]
  upto60comorbfirstdoses=[];upto60comorbseconddoses=[]
  for i in x:
    if i['firstdoseadministered']:firstdoses.append(int(i['firstdoseadministered']))
    else: firstdoses.append(0)
    if i['seconddoseadministered']:seconddoses.append(int(i['seconddoseadministered']))
    else: seconddoses.append(0)
    if i['frontlineworkersvaccinated1stdose']:frontlinefirstdoses.append(int(i['frontlineworkersvaccinated1stdose']))
    else: frontlinefirstdoses.append(0)
    if i['frontlineworkersvaccinated2nddose']:frontlineseconddoses.append(int(i['frontlineworkersvaccinated2nddose']))
    else: frontlineseconddoses.append(0)
    if i['healthcareworkersvaccinated1stdose']:hcwfirstdoses.append(int(i['healthcareworkersvaccinated1stdose']))
    else: hcwfirstdoses.append(0)
    if i['healthcareworkersvaccinated2nddose']:hcwseconddoses.append(int(i['healthcareworkersvaccinated2nddose']))
    else: hcwseconddoses.append(0)
    if i['over60years1stdose']:over60firstdoses.append(int(i['over60years1stdose']))
    else: over60firstdoses.append(0)
    if i['over60years2nddose']:over60seconddoses.append(int(i['over60years2nddose']))
    else: over60seconddoses.append(0)
    # ~ if i['to60yearswithco-morbidities1stdose']:upto60firstdoses.append(int(i['to60yearswithco-morbidities1stdose']))
    if i['over45years1stdose']:upto60firstdoses.append(int(i['over45years1stdose']))
    else: upto60firstdoses.append(0)
    # ~ if i['to60yearswithco-morbidities2nddose']:upto60seconddoses.append(int(i['to60yearswithco-morbidities2nddose']))
    if i['over45years2nddose']:upto60seconddoses.append(int(i['over45years2nddose']))
    else: upto60seconddoses.append(0)
    
    if i['to60yearswithco-morbidities1stdose']:upto60comorbfirstdoses.append(int(i['to60yearswithco-morbidities1stdose']))
    else: upto60comorbfirstdoses.append(0)
    if i['to60yearswithco-morbidities2nddose']:upto60comorbseconddoses.append(int(i['to60yearswithco-morbidities2nddose']))
    else: upto60comorbseconddoses.append(0)
    
    date=datetime.datetime.strptime(i['testedasof'],'%d/%m/%Y')
    dates.append(date)
    
  
  firstdoses=diffdata(firstdoses);seconddoses=diffdata(seconddoses);
  frontlinefirstdoses=diffdata(frontlinefirstdoses);frontlineseconddoses=diffdata(frontlineseconddoses);
  hcwfirstdoses=diffdata(hcwfirstdoses);hcwseconddoses=diffdata(hcwseconddoses);
  over60firstdoses=diffdata(over60firstdoses);over60seconddoses=diffdata(over60seconddoses);
  upto60firstdoses=diffdata(upto60firstdoses);upto60seconddoses=diffdata(upto60seconddoses)
  upto60comorbfirstdoses=diffdata(upto60comorbfirstdoses);upto60comorbseconddoses=diffdata(upto60comorbseconddoses)
  return list(zip(dates,firstdoses,seconddoses,frontlinefirstdoses,frontlineseconddoses,hcwfirstdoses,hcwseconddoses,over60firstdoses,over60seconddoses,upto60firstdoses,upto60seconddoses,upto60comorbfirstdoses,upto60comorbseconddoses))
  # ~ return list(zip(dates,firstdoses,seconddoses,frontlinefirstdoses,frontlineseconddoses,hcwfirstdoses,hcwseconddoses,over60firstdoses,over60seconddoses,upto60firstdoses,upto60seconddoses))

def vaccination_national_csv():
  x=csv.reader(open('tested_numbers_icmr_data.csv'));  info=[]
  for i in x: info.append(i)
  info=info[1:]
  x=[i for i in info if i[19]]
  firstdoses=[];seconddoses=[];dates=[]
  frontlinefirstdoses=[];frontlineseconddoses=[];hcwfirstdoses=[];hcwseconddoses=[]
  over60firstdoses=[];over60seconddoses=[];upto60firstdoses=[];upto60seconddoses=[]

  for i in x:
    if i[19]:firstdoses.append(int(i[19]))
    else: firstdoses.append(0)
    if i[20]:seconddoses.append(int(i[20]))
    else: seconddoses.append(0)
    if i[12]:frontlinefirstdoses.append(int(i[12]))
    else: frontlinefirstdoses.append(0)
    if i[13]:frontlineseconddoses.append(int(i[13]))
    else: frontlineseconddoses.append(0)
    if i[10]:hcwfirstdoses.append(int(i[10]))
    else: hcwfirstdoses.append(0)
    if i[11]:hcwseconddoses.append(int(i[11]))
    else: hcwseconddoses.append(0)
    if i[17]:over60firstdoses.append(int(i[17]))
    else: over60firstdoses.append(0)
    if i[18]:over60seconddoses.append(int(i[18]))
    else: over60seconddoses.append(0)
    if i[15]:upto60firstdoses.append(int(i[15]))
    else: upto60firstdoses.append(0)
    if i[16]:upto60seconddoses.append(int(i[16]))
    else: upto60seconddoses.append(0)
    date=datetime.datetime.strptime(i[1],'%d/%m/%Y')
    dates.append(date)
  
  
  firstdoses=diffdata(firstdoses);seconddoses=diffdata(seconddoses);
  frontlinefirstdoses=diffdata(frontlinefirstdoses);frontlineseconddoses=diffdata(frontlineseconddoses);
  hcwfirstdoses=diffdata(hcwfirstdoses);hcwseconddoses=diffdata(hcwseconddoses);
  over60firstdoses=diffdata(over60firstdoses);over60seconddoses=diffdata(over60seconddoses);
  upto60firstdoses=diffdata(upto60firstdoses);upto60seconddoses=diffdata(upto60seconddoses)
  return list(zip(dates,firstdoses,seconddoses,frontlinefirstdoses,frontlineseconddoses,hcwfirstdoses,hcwseconddoses,over60firstdoses,over60seconddoses,upto60firstdoses,upto60seconddoses))
def kerala_parse_vaccination(bulletin='',dump=False):
  if dump:
    cmd='pdftotext -layout "'+bulletin+'" tmp.txt';os.system(cmd)
    b=[i.strip() for i in open('tmp.txt').readlines() if i.strip()]
    find=[i for i in b if 'Age-Appropriate Group First Dose' in i]
    if find:
      b=b[b.index(find[0]):]
      date=b[0].replace('midnight','').strip().split()[-1].strip().replace('/21','')
    else:
      find=[i for i in b if 'Ageappropriategroup' in i]
      if not find: find=[i for i in b if 'Age-AppropriateGroupFirstDoseCoverageas' in i]
      if find:
        b=b[b.index(find[0]):]
        date=b[0].replace('midnight','').strip().split()[-1].strip().replace('/21','')
      
        
    x=[i for i in b if 'GrandTotal' in i]
    if x: x=x[0].split()
    else:
      x=[i for i in b if 'Grand Total' in i]
      if x: x=x[0].split()
    target=x[1];coverage=x[2]
    
    a=open('tmp.csv','a');  a.write(date+' , '+target+' , '+coverage+'\n');a.close()
    print('wrote vaccination data for '+date)
    return
  
  #read
  r=csv.reader(open('csv_dumps/kerala_vaccination.csv'))
  info=[]
  for i in r: info.append(i)
  info=info[1:]
  out=[]
  for i in info:
    date,a45target,a45vaccinated=i
    date=datetime.datetime.strptime(date.strip()+'/2021','%d/%m/%Y')
    out.append((date,int(a45target),int(a45vaccinated)))
  dates,t,a=zip(*out)
  percent=100*(np.array(a)/np.array(t))
  return list(zip(dates,t,a,percent))
def estimate_state_vaccination_timeseries(state='ct',vaccination_type='over60firstdoses',pop_multiple=''):
  if len(state)==2 and state in state_code_to_name: x=state;state=state_code_to_name[state];
  
  if not pop_multiple:
    if state in pop_growth_multiples:
      pop_multiple=pop_growth_multiples[state]
    else:
      pop_multiple=1.10;print('no growth mutiple known for %s. Using standard 10%% growth estimate (post 2011)' %(state))
  r=csv.reader(open('csv_dumps/national_vaccination_timeseries.csv'))
  info=[]
  for i in r: info.append(i)
  info=info[1:]
  
  dates=[];over60firstdoses=[];over45firstdoses=[];totdoses=[]
  for i in info:
    date=datetime.datetime.strptime(i[0]+'/2021','%d/%m/%Y')
    dates.append(date)
    over60firstdoses.append(int(i[1]))
    over45firstdoses.append(int(i[2]))
    totdoses.append(int(i[3]))
  
  totdoses=np.array(totdoses);dates=np.array(dates)
  over60firstdoses=np.array(over60firstdoses);over45firstdoses=np.array(over45firstdoses)
  
  frac=0
  if vaccination_type=='over60firstdoses':
    frac=over60firstdoses/totdoses
  elif vaccination_type=='over45firstdoses':
    frac=over45firstdoses/totdoses
    
  #Fraction is obtained nationally above, now apply to state-specific timeseries to get estimate
  
  y2=vaccination_state(state)
  y2=[i for i in y2 if i[0]<datetime.datetime(2021,5,5,0,0)]
  dates2,xx,cumstatedoses=zip(*y2)
  
  predict=np.int_(frac*np.array(cumstatedoses))
  
  predict_percent=0
  
  if vaccination_type=='over60firstdoses':
    predict_percent=100*(np.float_(predict)/(parse_census(state,'above60')[0]*pop_multiple))
  elif vaccination_type=='over45firstdoses':
    predict_percent=100*(np.float_(predict)/(parse_census(state,'above45')[0]*pop_multiple))
  
  predict_percent_unvaccinated=100-predict_percent
  
  return list(zip(dates2,predict,predict_percent,predict_percent_unvaccinated))
  

  
def parse_mohfw_bulletin(bulletin=''):
  cmd='pdftotext -nopgbrk -layout "'+bulletin+'" tmp.txt';os.system(cmd)
  b=[i.strip() for i in open('tmp.txt').readlines() if i.strip()]
  
  #get date
  
  date=[i for i in b if 'As on' in i]
  if not date: print('could not extract date from %s' %(buletin));return
  date=date[0].split('on')[1].split("’")[0].strip()
  date=date.replace('1st March','01 Mar') #malformed bulletin on mar1
  date=datetime.datetime.strptime(date+' 2021','%d %b %Y')
  date=date-datetime.timedelta(days=1) #correct by 1 day since bulletin comes next morning
  
  
  ind=[j for j in range(len(b)) if 'A & N Islands' in b[j]]
  if not ind: print('no index for AN islands!!');return
  ind=ind[0]
  b=[i.replace('&',' and ') for i in b[ind:]]
  info=[];fd={};sd={}
  for i in b:
    if not i[0].isnumeric(): continue
    bb=i.split()[1:]
    state=bb[0];index=1
    for k in bb[1:]:
      if not k[0].isnumeric(): state+=' '+k;index+=1
      else: break
    bb=bb[index:]
    # ~ bb=[i for i in bb if i]
    # ~ print(bb),print
    firstdoses=int(bb[0].replace(',',''))
    seconddoses=int(bb[1].replace(',',''))
    totaldoses=int(bb[2].replace(',',''))
    state=state.replace('A and N Islands','Andaman and Nicobar Islands')
    info.append((state,firstdoses,seconddoses,totaldoses))
    fd[state]=firstdoses
    sd[state]=seconddoses
  return (date,info,fd,sd)

    
  
def parse_census(state='Tamil Nadu',metric='mean age'):
  if len(state)==2 and state in state_code_to_name: x=state;state=state_code_to_name[state];
  if state=='Delhi':
    state='NCT of Delhi'
  r=csv.reader(open('census.csv'))
  info=[]
  for i in r: info.append(i)
  data=[i for i in info if i[0]==state]
#  print(len(data))
  if metric in ['above60','above45'] or metric.startswith('agedict'):
    data=data[1:-3]#exclude last 2 rows and initial one
    agedict={}
    for i in data:
      age=int(i[1])
      num_persons=int(i[2])
      num_males=int(i[3])
      num_females=int(i[4])
      agedict[age]=num_persons
      if metric=='agedictm': agedict[age]=num_males
      elif metric=='agedictf': agedict[age]=num_females
    if metric.startswith('agedict'): return agedict
    elif metric=='above60':
      tot_persons=sum(list(agedict.values()))
      above60=sum([agedict[i] for i in agedict if i>=60])
      try:frac=float('%.3f' %(float(above60)/tot_persons))
      except ZeroDivisionError: frac=0
      return (above60,frac*100)
    elif metric=='above45':
      tot_persons=sum(list(agedict.values()))
      above45=sum([agedict[i] for i in agedict if i>=45])
      try:frac=float('%.3f' %(float(above45)/tot_persons))
      except ZeroDivisionError: frac=0
      return (above45,frac*100)

  elif metric in ['mean age','tot_persons']:
    data=data[1:-3]#exclude last 2 rows and initial one
    agedict={}
    for i in data:
      age=int(i[1])
      num_persons=int(i[2])
      agedict[age]=num_persons
    tot_persons=sum(list(agedict.values()))
    if metric=='tot_persons': return tot_persons
    mean_age=0
    for i in agedict.keys():
      frac=float(agedict[i])/tot_persons
      mean_age+=frac*i
    return (mean_age,agedict,info,data)
  elif metric=='urbanization':
      data=data[0]
#      print(data[2],data[5])
      tot=int(data[2])
      urb=int(data[-3])
      return (100*float(urb)/tot,urb,tot,data)
  elif metric=='male':
      data=data[0]
#      print(data[2],data[5])
      tot=int(data[2])
      male=int(data[3])
      return (100*float(male)/tot,male,tot,data)

def get_cases_global(country='India',case_type='confirmed',do_moving_average=True,plot=False,plot_days=''):
    import csv
    fname='time_series_covid19_confirmed_global.csv'
    if case_type.startswith('deaths'): fname=fname.replace('confirmed','deaths')
    elif case_type.startswith('recovered'): fname=fname.replace('confirmed','recovered')
    r=csv.reader(open(fname))
    info=[]
    for i in r: info.append(i)
    dates=info[0][4:]
    dates=[datetime.datetime.strptime((d+'20').replace('/2120','/2021'),'%m/%d/%Y') for d in dates]
    cdata=[i for i in info if i[1]==country]
    if not cdata: print('info for %s not found!' %(country));return
    cdata=np.int_(cdata[0][4:])
    if '_delta' in case_type:
        cdata=np.diff(cdata)
        cdata=np.append(np.array([0]),cdata)
    if do_moving_average:
      cdata=moving_average(cdata)
    
    if plot:
      c=np.diff(cdata)
      dates=dates[1:]
      if plot_days: c=c[-1*plot_days:];dates=dates[-1*plot_days:]
      sp,ax=pylab.subplots()
      locator = mdates.AutoDateLocator(minticks=3, maxticks=7);formatter = mdates.ConciseDateFormatter(locator);
      ax.xaxis.set_major_locator(locator);ax.xaxis.set_major_formatter(formatter)
      ax.plot_date(dates,c,label='New daily cases in '+country+' (7-day MA)')
      pylab.xlabel('Date');pylab.ylabel('New cases');pylab.title('New daily cases in '+country+' (7-day MA)');pylab.legend()
      pylab.savefig(TMPDIR+'New daily cases in '+country+' (7-day MA).jpg');pylab.close()

    return (dates,cdata)

def get_population(state='Karnataka',district='Bengaluru Urban'):
    x=json.load(open('data-all.json'))
    dates=x.keys();dates=list(dates);dates.sort()
    last=x[dates[-1]]
    if not district:
        pop=last[state_name_to_code[state].upper()]['meta']['population']
    else:
        pop=last[state_name_to_code[state].upper()]['districts'][district]['meta']['population']
    pop=int(pop)
    return pop
def get_mortality_rate(state='Tamil Nadu',district='',return_full_series=False,do_dpm=False,plot=False,plot_days=''):
  if len(state)==2 and state in state_code_to_name: x=state;state=state_code_to_name[state];
  if not return_full_series:
    d=get_cases(state=state,case_type='deaths')
    c=get_cases(state=state,case_type='confirmed')
    return 100*(float(d)/c)
  else:
    if district:
        d=get_cases_district(state=state,district=district,case_type='deaths',return_full_series=True)
        c=get_cases_district(state=state,district=district,case_type='confirmed',return_full_series=True)

    else:
        d=get_cases(state=state,case_type='deaths',return_full_series=True)
        c=get_cases(state=state,case_type='confirmed',return_full_series=True)
    if do_dpm:
        pop=float(get_population(state,district))/1e6

    d=[i for i in d if i[1]>0]
    c=c[-1*len(d):]
    dates,d=zip(*d)
    dates2,c=zip(*c)
    m=100*(np.float64(d)/np.array(c))
    if do_dpm: dpm=(np.float64(d)/pop)
    x=list(zip(dates,m))

    if do_dpm: x=list(zip(dates,dpm))
    x=[i for i in x if i[0]>=datetime.datetime(2020,5,1,0,0)]
    dates,m=zip(*x)
    if plot:
      if plot_days:
          dates=dates[-1*plot_days:]
          m=m[-1*plot_days:]

      ax=pylab.axes()
      locator = mdates.AutoDateLocator(minticks=3, maxticks=7)
      formatter = mdates.ConciseDateFormatter(locator)
      ax.xaxis.set_major_locator(locator)
      ax.xaxis.set_major_formatter(formatter) 

      title=state
      if district: title+=' '+district+' district'
      title+=' mortality rate '
      ax.plot_date(pylab.date2num(dates),m,label='state')
      pylab.xlabel('Date');pylab.ylabel('Mortality Rate');pylab.title(title)
      pylab.savefig(TMPDIR+title+'.jpg');pylab.close()
    return x

def helper_get_pdf_urls(state='Tamil Nadu',start='15-03-2021',end='30-04-2021',alllinks=False,write=True):
    if len(state)==2 and state in state_code_to_name: x=state;state=state_code_to_name[state];
    start=datetime.datetime.strptime(start,'%d-%m-%Y')
    end=datetime.datetime.strptime(end,'%d-%m-%Y')
    x=json.load(open('state_test_data.json'))['states_tested_data']
    x=[i for i in x if i['state']==state]
    y=[i for i in x if datetime.datetime.strptime(i['updatedon'],'%d/%m/%Y')>=start and datetime.datetime.strptime(i['updatedon'],'%d/%m/%Y')<=end]
    y=[(i['source1'],datetime.datetime.strptime(i['updatedon'],'%d/%m/%Y')) for i in y]
    y2=[i[0] for i in y]
    if not alllinks: y2=[i for i in y2 if '.pdf' in i]
    
    y3=[i[1].strftime('%d-%m-%Y') for i in y if '.pdf' not in i[0]]
    if state=='Karnataka':       
      y3=[i for i in y if 't.co/' not in i]
    if not y3: y3='got pdf for all days between %s and %s' %(start.strftime('%d-%m'),end.strftime('%d-%m'))
    a=open('urls.txt','w')
    for i in y2: a.write(i+'\n')
    a.close()
    return y2,y3

def get_symptomatic(state='Telangana',asymp=False,plot=False):
    if len(state)==2 and state in state_code_to_name: x=state;state=state_code_to_name[state];
    x=json.load(open('state_test_data.json'))
    field="cumuilativenumberofsymptomaticcases"
    if asymp: field="cumuilativenumberofasymptomaticcases"
    d,c=zip(*[(i['updatedon'],i[field]) for i in x['states_tested_data'] if i[field] and i['state']==state])
    d=list(d);c=list(c)
    inc=list(np.diff(np.int_(c)))
    c2=c[:1];c2.extend(inc)
    if plot:
        d=d[1:];c2=c2[1:]
        d=[datetime.datetime.strptime(i,'%d/%m/%Y') for i in d]
        c3=moving_average(c2)
        if state=='Telangana':
            d2,yy,ic=zip(*get_people_in_icus(state))
            d2=[datetime.datetime.strptime(i,'%d/%m/%Y') for i in d2]
            ic=moving_average(ic)
        mylabel='Symptomatic Cases (7-day MA)'
        if asymp: mylabel='Asymptomatic cases (7-day MA)'
        plot2(d,c3,d2,ic,label1=mylabel,label2='Patients in ICUs',state=state)



    return d,c,c2

def mortality_analysis():
  states=['Bihar','Tamil Nadu','Karnataka','Uttar Pradesh','Punjab','Assam','Odisha','Madhya Pradesh','Gujarat','Andhra Pradesh','Madhya Pradesh','Maharashtra']
  #states=['Kerala','Bihar','Tamil Nadu','Karnataka','Uttar Pradesh','Delhi','Punjab','Assam','Odisha','Madhya Pradesh','Gujarat','Andhra Pradesh','Madhya Pradesh','Maharashtra']
  #states=['Kerala','Bihar','Tamil Nadu','Uttar Pradesh','Madhya Pradesh','Gujarat','Maharashtra']
  info=[]
  for state in states:
    mortality_rate=get_mortality_rate(state=state)
    urbanization=parse_census(state=state,metric='urbanization')[0]
    males=parse_census(state=state,metric='male')[0]
    mean_age=parse_census(state=state,metric='mean age')[0]
    date_first_100=get_cases(state=state,case_type='first100deaths')
    info.append((state,mortality_rate,urbanization,males,mean_age,date_first_100))
 
  print('gathered data')
  states,mortality_rates,urbanizations,maless,mean_ages,dates_first_100=zip(*info)
  #plot
  for i in info:
    state,mortality_rate,urbanization,males,mean_age,d1=i
    #print(mortality_rate,mean_age)
    pylab.scatter(mean_age,mortality_rate,label=state)
    ylabel='Mortality Rate (oct 14)';xlabel='Mean age (2011 census)';title='Mortality Rate vs Mean age for Indian states'
    pylab.xlabel(xlabel);pylab.ylabel(ylabel);pylab.title(title);pylab.legend(fontsize=6)
  helper_plot_linear_fit(mean_ages,mortality_rates)
  pylab.savefig(TMPDIR+'mortality rate vs mean age.jpg');pylab.close()
  for i in info:
    state,mortality_rate,urbanization,males,mean_age,d1=i
    #print(mortality_rate,urbanization)
    pylab.scatter(urbanization,mortality_rate,label=state)
    ylabel='Mortality Rate (oct 14)';xlabel='Urban population percentagee (2011 census)';title='Mortality Rate vs urban population percentage  for Indian states'
    pylab.xlabel(xlabel);pylab.ylabel(ylabel);pylab.title(title);pylab.legend(fontsize=6)
  helper_plot_linear_fit(urbanizations,mortality_rates)
  pylab.savefig(TMPDIR+'mortality rate vs urbanization.jpg');pylab.close()
  for i in info:
    state,mortality_rate,urbanization,males,mean_age,d1=i
    #print(mortality_rate,males)
    pylab.scatter(males,mortality_rate,label=state)
    ylabel='Mortality Rate (oct 14)';xlabel='Male population percentagee (2011 census)';title='Mortality Rate vs Male population percentage  for Indian states'
    pylab.xlabel(xlabel);pylab.ylabel(ylabel);pylab.title(title);pylab.legend(fontsize=6)
  helper_plot_linear_fit(maless,mortality_rates)
  pylab.savefig(TMPDIR+'mortality rate vs males.jpg');pylab.close()

  ax=pylab.axes()
  locator = mdates.AutoDateLocator(minticks=3, maxticks=7)
  formatter = mdates.ConciseDateFormatter(locator)
  ax.xaxis.set_major_locator(locator)
  ax.xaxis.set_major_formatter(formatter) 

  for i in info:
    state,mortality_rate,urbanization,males,mean_age,d1=i
    #print(mortality_rate,males)
    ax.plot_date(pylab.date2num(d1),mortality_rate,'.',label=state)
    ylabel='Mortality Rate (oct 14)';xlabel='Date of firrt 300 deaths';title='Mortality Rate vs Date of 1st 300 deaths for Indian states'
    pylab.xlabel(xlabel);pylab.ylabel(ylabel);pylab.title(title);pylab.legend(fontsize=6)
  helper_plot_linear_fit(pylab.date2num(dates_first_100),mortality_rates,xtype='date')
  pylab.savefig(TMPDIR+'mortality rate vs first 300.jpg');pylab.close()
  return info


def get_tests_national(return_full_series=True):
  r=csv.reader(open('tested_numbers_icmr_data.csv'))
  info=[]
  for i in r: info.append(i)
  info=info[1:];tests=[]
  cnt=0
  for i in info:
    try:date=datetime.datetime.strptime(i[0].split()[0].strip(),'%d/%m/%Y');
    except:
      print('error getting date form %s' %(str(i)))
      sys.exit(1)
    if i[4]: cumtests=int(i[4])
    else: cumtests=int(info[cnt-1][4])
    tests.append((date,cumtests))
    cnt+=1
  dates,t=zip(*tests)
  t2=zip(dates[1:],np.diff(t))
  t=[tests[0]];  t.extend(t2)
  return t
def get_cases_national(case_type='confirmed',return_full_series=True):
  x=json.load(open('national_data.json'))['cases_time_series']
  info=[]
  for i in x:
    date=i['dateymd'];y=0    
    date=datetime.datetime.strptime(date,'%Y-%m-%d')
    y=''
    if case_type=='confirmed': y=int(i['dailyconfirmed'])
    elif case_type in ['deaths','death']: y=int(i['dailydeceased'])
    elif case_type in ['recovered']: y=int(i['dailyrecovered'])
    elif case_type in ['active']: y=int(i['dailyconfirmed'])-int(i['dailyrecovered'])-int(i['dailydeceased'])
    if y: info.append((date,y))
  if case_type in ['tested','tests']:
    x=json.load(open('national_data.json'))['tested']
    dd=[];yy=[]
    for i in x:
      
      
      if i['totalsamplestested']: 
        date=datetime.datetime.strptime(i['updatetimestamp'].split()[0],'%d/%m/%Y')
        yy.append(int(i['totalsamplestested']));dd.append(date)
    y=np.diff(yy)
    info=list(zip(dd[1:],y))
  return info

def get_testing_delta():
  x=json.load(open('data-all.json'))
  d=list(x.keys());d.sort()
  # ~ dates=[datetime.datetime.strptime(i,'%Y-%m-%d') for i in d];
  # ~ dates=[i for i in dates if i>=datetime.datetime(2020,8,1,0,0)]
  tested_states=[]
  for date in d:
    dt=datetime.datetime.strptime(date,'%Y-%m-%d')
    if dt<datetime.datetime(2020,8,1,0,0): continue
    tested=0;tested_national=0
    for state in x[date]:
      if state=='TT':
        if 'delta' in x[date][state] and 'tested' in x[date][state]['delta']:
          tested_national=x[date][state]['delta']['tested']
      else:        
        if 'delta' in x[date][state] and 'tested' in x[date][state]['delta']:
          tested+=x[date][state]['delta']['tested']
    tested_states.append((dt,tested_national,tested,tested-tested_national))
  return tested_states
      
# ~ def fix_faulty_json():
  # ~ b=[i for i in open('states_daily.json').readlines()]
  # ~ b[22165]=b[22165].replace('"0"','"135"')
  # ~ b[22294]=b[22294].replace('"0"','"113"')
  # ~ b[22423]=b[22423].replace('"0"','"104"')
  # ~ b[22552]=b[22552].replace('"0"','"116"')
  # ~ b[22681]=b[22681].replace('"0"','"128"')
  # ~ a=open('states_daily.json','w')
  # ~ for i in b: a.write(i)
  # ~ a.close()
##date must be given as 01/09/2020 for September 1,2020
##State must be fullname (see dict above)
def get_cases_district(state='Karnataka',district='Bengaluru Urban',date='01/09/2020',case_type='confirmed',return_full_series=True,verbose=False):
  if len(state)==2 and state in state_code_to_name: state=state_code_to_name[state];
  r=csv.reader(open('districts.csv'))
  info=[]
  for i in r: info.append(i)
  info=[i for i in info if district==i[2] and state==i[1]]
  confirmed=[];recovered=[];deaths=[];dates=[];actives=[]
  for i in info:
    date=datetime.datetime.strptime(i[0],'%Y-%m-%d')
    confirmed.append(i[3]);    recovered.append(i[4]);    deaths.append(i[5])
    active=int(i[3])-int(i[4])-int(i[5])
    actives.append(active)
    dates.append(date)
  dates=dates[1:]
  confirmed=np.diff(np.int_(confirmed))
  recovered=np.diff(np.int_(recovered))
  deaths=np.diff(np.int_(deaths))
  if case_type in ['confirmed']:    return list(zip(dates,confirmed))
  elif case_type in ['recovered']:    return list(zip(dates,recovered))
  elif case_type in ['deaths']:    return list(zip(dates,deaths))
  elif case_type in ['active']:    return list(zip(dates,actives[1:]))
  
  
  # ~ x=json.load(open('data-all.json'))
  # ~ d=list(x.keys());d.sort()
  # ~ dates=[datetime.datetime.strptime(i,'%Y-%m-%d') for i in d];
  # ~ state_code=state_name_to_code[state].upper()
  # ~ returned=[]

  # ~ first30=False
  # ~ if case_type=='first30deaths' : first30=True;case_type='deaths' 
  
  # ~ for date in d:
    # ~ dt=datetime.datetime.strptime(date,'%Y-%m-%d')
    # ~ if dt<=datetime.datetime(2020,4,1,0,0): continue
    # ~ if  not (state_code in x[date] and 'districts' in x[date][state_code]) : continue
    # ~ state_data=x[date][state_code]['districts']

    
    # ~ if district in state_data:
      # ~ district_data=state_data[district]
      # ~ if not ('total' in district_data and 'delta' in district_data): continue
      # ~ tested=0;tested_delta=0;deaths_delta=0;deaths=0;recovered=0
      # ~ confirmed=district_data['total']['confirmed']
      # ~ if 'recovered' in district_data['total']: recovered=district_data['total']['recovered']
      # ~ if 'deceased' in district_data['total']:  deaths=district_data['total']['deceased']
      # ~ if 'tested' in district_data['total']: tested=district_data['total']['tested']
      
      # ~ active=confirmed-recovered-deaths

      # ~ if not ('recovered' in district_data['delta'] and 'confirmed' in district_data['delta']): continue
      # ~ confirmed_delta=district_data['delta']['confirmed']
      # ~ try:
        # ~ recovered_delta=district_data['delta']['recovered']
      # ~ except:
        # ~ print(('error getting recovered_delta on date: '+date))
        # ~ print((district_data['delta']))
        # ~ return
      # ~ if 'deceased' in district_data['delta']: deaths_delta=district_data['delta']['deceased']
      # ~ active_delta=confirmed_delta-recovered_delta-deaths_delta
      # ~ if 'tested' in district_data['delta']: tested_delta=district_data['delta']['tested']

      # ~ if case_type=='confirmed_delta': returned.append((dt,confirmed_delta))
      # ~ elif case_type=='recovered_delta': returned.append((dt,recovered_delta))
      # ~ elif case_type=='deaths_delta': returned.append((dt,deaths_delta))
      # ~ elif case_type=='active_delta': returned.append((dt,active_delta))
      # ~ elif case_type=='tested_delta': returned.append((dt,tested_delta))
      # ~ elif case_type=='recovered': returned.append((dt,recovered))
      # ~ elif case_type=='deaths': returned.append((dt,deaths))
      # ~ elif case_type=='active': returned.append((dt,active))
      # ~ elif case_type=='tested': returned.append((dt,tested))
      # ~ elif case_type=='confirmed': returned.append((dt,confirmed))
    # ~ else:
      # ~ continue
  # ~ del x
  # ~ if first30:
    # ~ date=''
    # ~ for i in returned:
      # ~ if i[1]>=30: return i[0]
  # ~ return returned

def plot_table(data,rows,columns,fontsize=15,scale=1.2):
  pylab.close();
  sp,ax=pylab.subplots();
  table=pylab.table(cellText=data,rowLabels=rows,colLabels=columns,loc='center');
  table.auto_set_font_size(False);table.set_fontsize(fontsize);
  table.auto_set_column_width(col=list(range(1,4)));table.scale(scale,scale);
  ax.axis('tight');ax.axis('off');
  pylab.show();

def plotex(dates,data,dates2=np.array([]),data2=np.array([]),label='',label2='',color='blue',color2='red',state='',linear_fit=False,plot_days='',extrapolate='',date_label=''):
  
  if type(dates[0])==datetime.datetime: dates=pylab.date2num(dates)
  if type(dates) in [tuple,list]: dates=np.array(dates)
  if type(dates2) in [tuple,list]: dates2=np.array(dates2)
  if dates2.any(): dates2=np.array(dates2);data2=np.array(data2)
  if dates2.any() and type(dates2[0])==datetime.datetime: 
    dates2=pylab.date2num(dates2)
    if plot_days: 
      dates2=dates2[-1*plot_days:]
      data2=data2[-1*plot_days:]
  if plot_days:
    dates=dates[-1*plot_days:]
    data=data[-1*plot_days:]
  ax=pylab.axes()
  locator = mdates.AutoDateLocator(minticks=3, maxticks=7)
  formatter = mdates.ConciseDateFormatter(locator)
  # ~ formatter = mdates.DateFormatter('%d-%m')
  ax.xaxis.set_major_locator(locator)
  ax.xaxis.set_major_formatter(formatter) 

  ax.set_xlabel('Date');
  if date_label: ax.set_xlabel(date_label)
  ax.set_ylabel(label)
  ax.plot_date(dates,data,color=color,label=label)
  #ax.tick_params(axis='y', labelcolor=color)

  if dates2.any():
      ax.plot_date(dates2,data2,color=color2,label=label2)
  if linear_fit:
      if extrapolate: helper_plot_linear_fit(dates,data,extrapolate=extrapolate)
      else: pass;#     helper_plot_linear_fit(dates,data)
  #ax.legend(loc='lower left',fontsize=6)
  ax.legend(fontsize=7)
  title=label
  if label2: title+=' vs '+label2
  if state: title+=' in '+state
  # ~ title+=' over time'
  title=title.replace('(7-day MA)','')
  pylab.title(title);  
  pylab.savefig(TMPDIR+title+'.jpg',dpi=100)
  pylab.close()


def plot2(dates,data,dates2,data2,label1='',label2='',state='',color1='blue',color2='red',draw_vline=False,plot_days=''):
    if len(state)==2 and state in state_code_to_name: state=state_code_to_name[state];
    if plot_days:
        dates=dates[-1*plot_days:]
        dates2=dates2[-1*plot_days:]
        data=data[-1*plot_days:]
        data2=data2[-1*plot_days:]

    if type(dates[0])==datetime.datetime: dates=pylab.date2num(dates)
    if type(dates2[0])==datetime.datetime: dates2=pylab.date2num(dates2)
    sp,ax=pylab.subplots()

    color = color1
    locator = mdates.AutoDateLocator(minticks=3, maxticks=7)
    # ~ formatter = mdates.ConciseDateFormatter(locator)
    formatter = mdates.ConciseDateFormatter(locator)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(formatter) 

    ax.set_xlabel('Date')
    ax.set_ylabel(label1,color=color)
    ax.plot_date(dates,data,color=color,label=label1)
    ax.tick_params(axis='y', labelcolor=color)
    
    if draw_vline:
      # ~ ax.vlines(pylab.date2num([datetime.datetime(2021, 3, 1, 0, 0)]),min(data)-0.5,max(data)+0.5,label='Elderly vaccinations begin',color='green',linestyles='dashed',linewidth=4)
      ax.vlines(pylab.date2num([datetime.datetime(2021, 5, 6, 0, 0)]),min(data),max(data)+3,label='Approximate national peak',color='grey',linestyles='dashed',linewidth=5)
    
    ax.legend(loc='upper left',fontsize=6)

    ax2=ax.twinx()
    color = color2
    locator = mdates.AutoDateLocator(minticks=3, maxticks=7)
    # ~ formatter = mdates.ConciseDateFormatter(locator)
    formatter = mdates.ConciseDateFormatter(locator)
    ax2.xaxis.set_major_locator(locator)
    ax2.xaxis.set_major_formatter(formatter) 

    ax2.set_ylabel(label2,color=color)
    ax2.plot_date(dates2,data2,color=color,label=label2)
    ax2.tick_params(axis='y', labelcolor=color)
    ax2.legend(loc='upper right',fontsize=6)
    
    title=''
    if state: title+=state+' '
    title+=label1.replace('(7-day MA)','')+' vs '+label2.replace('(7-day MA)','')
    pylab.title(title);  
    pylab.savefig(TMPDIR+title+'.jpg',dpi=100)
    pylab.close()

def get_beds(state='West Bengal'):
  if len(state)==2 and state in state_code_to_name: x=state;state=state_code_to_name[state];
  x=json.load(open('state_test_data.json'))
  if state in ['West Bengal']:
    x=[i for i in x['states_tested_data'] if i['state']==state and  i['bedsoccupiednormalisolation']]
    dates=[];bed_util=[];bed_cap=[]

    for i in x:
        dates.append(datetime.datetime.strptime(i['updatedon'],'%d/%m/%Y'))
        bed_cap.append(int(i['totalnumbedsnormalisolation']))
        u=int(bed_cap[-1]*0.01*float(i['bedsoccupiednormalisolation'].replace('%','')))
        bed_util.append(u)
    return list(zip(dates,bed_cap,bed_util)) 
  elif state in ['Uttar Pradesh']:
    x2=[(i['updatedon'],0,i['casesoutsidehomeisolationi.einstitutionalisolationhospitaletc.']) for i in x['states_tested_data'] if i['casesoutsidehomeisolationi.einstitutionalisolationhospitaletc.'] and i['state']==state]
    y=[(datetime.datetime.strptime(i[0],'%d/%m/%Y'),i[1],int(i[2])) for i in x2]
    return y



def wb_analysis(plot=False,plot_days=''):
    x=json.load(open('state_test_data.json'))
    x=[i for i in x['states_tested_data'] if i['state']=='West Bengal' if i['bedsoccupiednormalisolation'] and i['totalnumicubeds'] and i['totalnumbedsnormalisolation'] and i['totalnumventilators']]
    dates=[];bed_cap=[];bed_util=[];icu_cap=[];vent_cap=[]
    ppe=[];n95=[]

    for i in x:
        dates.append(datetime.datetime.strptime(i['updatedon'],'%d/%m/%Y'))
        icu_cap.append(int(i['totalnumicubeds']))
        vent_cap.append(int(i['totalnumventilators']))
        bed_cap.append(int(i['totalnumbedsnormalisolation']))
        u=int(bed_cap[-1]*0.01*float(i['bedsoccupiednormalisolation'].replace('%','')))
        bed_util.append(u)
        ppe.append(int(i['totalppe']))
        n95.append(int(i['totaln95masks']))
  
    dates2=pylab.date2num(dates)

    dates3,actives=zip(*get_cases('West Bengal',case_type='active',return_full_series=True))
    dates4,deaths=zip(*get_cases('West Bengal',case_type='deaths',return_full_series=True))
    deaths=moving_average(np.diff(deaths));dates4=dates4[1:];
    actives=moving_average(actives)
    ppe=np.diff(ppe)
    n95=np.diff(n95)

    if plot_days:
        deaths=deaths[-1*plot_days:]
        actives=actives[-1*plot_days:]
        bed_util=bed_util[-1*plot_days:]
        bed_cap=bed_cap[-1*plot_days:]
        n95=n95[-1*plot_days:]
        ppe=ppe[-1*plot_days:]
        dates2=dates2[-1*plot_days:]
        dates3=dates3[-1*plot_days:]
        dates4=dates4[-1*plot_days:]
    #util vs cap
    plot2(dates2,moving_average(bed_util),dates2,moving_average(bed_cap),label1='hospital beds used (7-day MA)',label2='hospital bed capacity (7-day MA)',state='West Bengal')
    # ~ plot2(dates2,moving_average(bed_util),dates2,moving_average(ppe),label1='hospital beds used (7-day MA)',label2='daily PPE (7-day MA)',color2='maroon',state='West Bengal')
    # ~ plot2(dates2,moving_average(bed_util),dates2,moving_average(n95),label1='hospital beds used (7-day MA)',label2='daily N95 masks (7-day MA)',color2='grey',state='West Bengal')
    plot2(dates2,moving_average(bed_util),dates3,actives,label1='hospital beds used (7-day MA)',label2='Active cases (7-day MA)',color2='orange',state='West Bengal')
    plot2(dates2,moving_average(bed_util),dates4,deaths,label1='hospital beds used (7-day MA)',label2='Daily Deaths (7-day MA)',color2='red',state='West Bengal')


    return (dates,icu_cap,vent_cap,bed_cap,bed_util,ppe,n95)



def get_cases(state='Telangana',date='14/10/2020',case_type='active',return_full_series=False,verbose=False):
  if len(state)==2 and state in state_code_to_name: x=state;state=state_code_to_name[state];
  x=json.load(open(BASEDIR+'states_daily.json'))['states_daily']

  target_datetime=datetime.datetime.strptime(date,'%d/%m/%Y')
  state_code=state_name_to_code[state]
  if case_type=='first100deaths':
    return_full_series=True

  #get all confirmed cases till date
  confirmed=0;recovered=0;deaths=0;active=0;
  confirmed_prev=0;recovered_prev=0;deaths_prev=0;active_prev=0;

  if return_full_series:
    confirmed_series={};recovered_series={};deaths_series={};active_series={};
    target_datetime=datetime.datetime.strptime(x[-1]['dateymd'],'%Y-%m-%d');#choose last date available
    
  for i in x:
    datetime_i=datetime.datetime.strptime(i['dateymd'],'%Y-%m-%d')
    if datetime_i<target_datetime:
      if   i['status']=='Deceased':  deaths+=int(i[state_code]);deaths_prev+=int(i[state_code])
      elif i['status']=='Recovered': recovered+=int(i[state_code]);recovered_prev+=int(i[state_code]);
      elif i['status']=='Confirmed': confirmed+=int(i[state_code]);confirmed_prev+=int(i[state_code]);
      active=confirmed-deaths-recovered;active_prev=active

      if return_full_series:
        confirmed_series[datetime_i]=confirmed;recovered_series[datetime_i]=recovered;
        deaths_series[datetime_i]=deaths;active_series[datetime_i]=active
    if datetime_i==target_datetime:
      if   i['status']=='Deceased':  deaths+=int(i[state_code])
      elif i['status']=='Recovered': recovered+=int(i[state_code])
      elif i['status']=='Confirmed': confirmed+=int(i[state_code])
      active=confirmed-deaths-recovered

      if return_full_series:
        confirmed_series[datetime_i]=confirmed;recovered_series[datetime_i]=recovered;
        deaths_series[datetime_i]=deaths;active_series[datetime_i]=active

  if return_full_series:
    x=[]
    for date in confirmed_series: x.append((date,confirmed_series[date]))
    confirmed_series=x;confirmed_series.sort()
    x=[]
    for date in deaths_series: x.append((date,deaths_series[date]))
    deaths_series=x;deaths_series.sort()
    x=[]
    for date in active_series: x.append((date,active_series[date]))
    active_series=x;active_series.sort()
    x=[]
    for date in recovered_series: x.append((date,recovered_series[date]))
    recovered_series=x;recovered_series.sort()
  if case_type=='first100deaths':
    for i in deaths_series:
      date=i[0]
      if i[1]>=30: break
    if verbose: print('%s passed its 1st 300 deaths on %s' %(state,datetime.datetime.strftime(date,'%d-%m')))
    return date
  elif case_type=='active':
    if verbose: print(('Active cases in %s on %s were %d' %(state,date,active)))
    if return_full_series:  return active_series
    else:                   return active
  elif case_type=='confirmed':
    if verbose: print(('Total cases in %s on %s were %d' %(state,date,confirmed)))
    if return_full_series:  return confirmed_series
    else:                   return confirmed
  elif case_type=='recovered':
    if verbose: print(('Recovered cases in %s on %s were %d' %(state,date,recovered)))
    if return_full_series:  return recovered_series
    else:                   return recovered
  elif case_type=='deaths':
    if verbose: print(('Deaths in %s on %s were %d' %(state,date,deaths)))
    if return_full_series:  return deaths_series
    else:                   return deaths
  if case_type=='active_day':
    active_day=active-active_prev
    if verbose: print(('Active cases in %s on %s were %d' %(state,date,active_day)))
    return active_day
  elif case_type=='confirmed_day':
    confirmed_day=confirmed-confirmed_prev
    if verbose: print(('new cases in %s on %s were %d' %(state,date,confirmed_day)))
    return confirmed_day    
  elif case_type=='recovered_day':
    recovered_day=recovered-recovered_prev
    if verbose: print(('Recovered cases in %s on %s were %d' %(state,date,recovered_day)))
    return recovered_day
  elif case_type=='deaths_day':
    deaths_day=deaths-deaths_prev
    if verbose: print(('Deaths in %s on %s were %d' %(state,date,deaths_day)))
    return deaths_day

global_karnataka_case_series='';global_karnataka_case_date_series='';global_karnataka_case_number_series=''
#cache this to avoid repeated file reads
if 'covid19india_data_parser' in os.path.abspath('.'):
  global_karnataka_case_series=get_cases(state='Karnataka',case_type='confirmed',return_full_series=True,verbose=False)
  global_karnataka_case_date_series=[i[0] for i in global_karnataka_case_series]
  global_karnataka_case_number_series=[i[1] for i in global_karnataka_case_series]
  
def highlight(text):
  highlight_begin=colorama.Back.BLACK+colorama.Fore.WHITE+colorama.Style.BRIGHT
  highlight_reset=colorama.Back.RESET+colorama.Fore.RESET+colorama.Style.RESET_ALL
  return highlight_begin+text+highlight_reset
def helper_download_karnataka_bulletin(twitter_link,debug=False):
  twitter_links=[]
  if os.path.exists(twitter_link):
    twitter_links=[i.strip() for i in open(twitter_link).readlines() if i.strip()]
  else: 
    twitter_links=[twitter_link]
  for twitter_link in tqdm.tqdm(twitter_links):
    print('processing '+twitter_link)
    x=requests.get(twitter_link)
    url=x.url
    file_id=url.split('/d/')[1].split('/')[0]
    google_drive_url='https://docs.google.com/uc?export=download&id='+file_id
    download_cmd='wget -q --no-check-certificate "'+google_drive_url+'" -O tmp.pdf'
    if debug: print(download_cmd)
    os.system(download_cmd)
    try:(bulletin_date,annex_range)=karnataka_bulletin_parser('tmp.pdf',return_date_only=True)
    except:bulletin_date='';print('could not find bulletin date')
    if debug: print(('bulletin_date: '+str(bulletin_date)))
    if not bulletin_date:
      print('could not find date for bulletin. Using tmp format')
      bulletin_date_string=datetime.datetime.now().strftime('%H-%s')
    else:    
      bulletin_date_string=datetime.datetime.strftime(bulletin_date,'%m_%d_%Y')
    os.system('cp -v tmp.pdf "'+bulletin_date_string+'.pdf"')

def helper_download_delhi_bulletin(link,debug=False):
  download_cmd='wget -q --no-check-certificate "'+link+'" -O tmp.pdf'
  if debug: print(download_cmd)
  os.system(download_cmd)
  bulletin_date=delhi_bulletin_parser('tmp.pdf',return_date_only=True)
  if debug: print(('bulletin_date: '+str(bulletin_date)))
  if not bulletin_date:
    print('could not find date for bulletin. Using tmp format')
    bulletin_date_string=datetime.datetime.now().strftime('%H-%s')
  else:    
    bulletin_date_string=datetime.datetime.strftime(bulletin_date,'%m_%d_%Y')
  os.system('cp -v tmp.pdf "'+bulletin_date_string+'.pdf"')


def delhi_parse_vent(datatype='ventilator',plot=False,extrapolate=''):
    b=[i.strip() for i in open('parsed_text_clippings/delhidata.txt').readlines() if i.strip()]
    info=[];chunk=[]
    for i in b:
        if 'on date' in i and chunk:
            info.append(chunk)
            chunk=[]
            chunk.append(i)
        else:
            chunk.append(i)
    info.append(chunk); #last
    
    info2=[]
    for chunk in info:
        date=chunk[0].split('date:')[1].strip()
#        print(date)
        date=date.replace(',','').split()[:3:2]
        try:date=datetime.datetime.strptime(' '.join(date),'%d-%m-%Y %H:%M')
        except:
            print(date)
            continue
        dtype=chunk[0].split(',')[-1].strip()
        if 'icu' in dtype:
            dtype='icu'
        else:
            dtype='ventilator'
        total=int(chunk[1].split(':')[1].strip())
        occupied=int(chunk[2].split(':')[1].strip())
        vacant=int(chunk[3].split(':')[1].strip())
        if dtype=='ventilator' and datatype in ['ventilator']:
            info2.append((date,total,occupied))
        if dtype=='icu' and datatype in ['icu']:
            info2.append((date,total,occupied))
    if plot:
        dates,total,occupied=zip(*info2)
        plotex(dates,occupied,np.array(dates),total,label='Occupied '+datatype,label2='Capacity of '+datatype,state='Delhi',linear_fit=True,extrapolate=extrapolate)
        #plotex(dates,occupied,np.array(dates),total,label='Occupied '+datatype,label2='Capacity of '+datatype,state='Delhi',linear_fit=True,extrapolate='')
    return info2
def mhpolice_parse_csv():
    import csv,datetime
    r=csv.reader(open('csv_dumps/MH_Police_infections.csv'))
    info=[];skip=True
    for i in r: 
        #if skip: skip=False;continue
        x=i
        y=datetime.datetime(int(x[0].split('-')[0]),int(x[0].split('-')[1]),int(x[0].split('-')[2]),0,0)
        infections=int(x[1]);deaths=int(x[2])
        info.append((y,infections,deaths))
    return info
 
def delhi_parse_csv():
    import csv,datetime
    r=csv.reader(open('csv_dumps/Delhi_Jun18_Oct27.csv'))
    info=[];info0=[];skip=True
    for i in r: info0.append(i)
    for i in info0[1:]:
        #if skip: skip=False;continue
        x=i
        try: y=datetime.datetime(int(x[0].split('-')[0]),int(x[0].split('-')[1]),int(x[0].split('-')[2]),0,0)
        except: 
          print('failed in '+str(i))
        x[0]=y
        a1,a2,a3,a4,a5,a6,a7,a8,a9,a10,a11,a12=x
        info.append(delhi_status(a1,int(a2),int(a3),int(a4),int(a5),int(a6),int(a7),int(a8),int(a9),int(a10),int(a11),int(a12)))

    return info
    
def delhi_bulletin_parser(bulletin='09_15_2020.pdf',return_date_only=False,restricted_parse=True,debug=False):
  cmd='pdftotext -layout "'+bulletin+'" tmp.txt';os.system(cmd)
  b=[i.strip() for i in open('tmp.txt').readlines() if i.strip()]

  date_string=[i for i in b if '2020' in i or '2021' in i]
  if not date_string:
    print(('could not find date for bulletin ',bulletin))
    return
  date_string=date_string[0].lower()
  if debug: print('date_string: ',date_string)
  try:
    if '/' in date_string:
      date_string=date_string.split('/')[1].replace(')','').replace('(','').replace(',',' ').replace('2021',' ').strip()
    else:
      date_string=date_string.replace(')','').replace('(','').replace(',',' ').replace('2021',' ').strip()
  except:
    print(('error getting date for bulletin: '+bulletin+' with string: '+date_string))
  
  # ~ date_string=date_string.replace('st','').replace('nd','').replace('rd','').replace('th','')
  if debug: print('date_string: ',date_string)
  
  
  if len(date_string.split())==1: #all jumbled        
    for mm in ['june','july','august','september','october','november']: date_string=date_string.replace(mm,'')
    day=date_string
    month_string=date_string.split()[0].strip().lower()
    # ~ print date_string,month_string
    month_string=month_string[:month_string.index(date_string)]
  else:
    day=date_string.split()[1]
    month_string=date_string.split()[0].strip().lower()
  day=day.replace('th','').replace('nd','').replace('st','').replace('rd','').strip()
  day=int(day)
  
  
  month=0
  month={'december':12,'january':1,'february':2,'march':3,'april':4,'may':5,'june':6,'july':7}.get(month_string)
  
  date=datetime.datetime(2021,month,day,0,0)

  if return_date_only: return date

  hos=[i for i in b if i.lower().startswith('hospital')]
  if not hos:
    print(('could not find data in bulletin %s for covid hospitals' %(bulletin)))
    return
  hos=hos[0];hos_capacity=hos.split()[-3];hos_used=hos.split()[-2];

  if restricted_parse:
    dcc_capacity='0';dcc_used='0';dchc_capacity='0';dchc_used='0';
    total='0';rtpcr='0';rapid='0';cz='0';amb='0'
  else:
    dcc=[i for i in b if i.lower().startswith('dedicated covid care centre')]
    if not dcc:
      print(('could not find data in bulletin %s for DCCC' %(bulletin)))
      return
    dcc=dcc[0];dcc_capacity=dcc.split()[-3];dcc_used=dcc.split()[-2];
  
    dchc=[i for i in b if i.lower().startswith('dedicated covid health')]
    if not dchc:
      print(('could not find data in bulletin %s for DCHC' %(bulletin)))
      return
    dchc=dchc[0];dchc_capacity=dchc.split()[-3];dchc_used=dchc.split()[-2];
  
    tt=[i for i in b if i.lower().startswith('tests conducted today')]  
    rtpcr=0;rapid=0;total=0
    if tt: #old type
      total=tt[0].split()[-1]
      total=int(total)
    else:
      rtpcr=[i for i in b if i.lower().startswith('rtpcr')]
      if not rtpcr:
        print(('could not find data in bulletin %s for RTPCR' %(bulletin)))
        return
      rtpcr=rtpcr[0].split()[-1]
  
      rapid=[i for i in b if i.lower().startswith('rapid antigen')]
      if not rapid:
        print(('could not find data in bulletin %s for rapid tests' %(bulletin)))
        return
      rapid=rapid[0].split()[-1]
      total=int(rapid)+int(rtpcr)
  
    cz=[i for i in b if 'number of containment zones' in i.lower()]
    if not cz:
      print(('could not find data in bulletin %s for containment zones' %(bulletin)))
      return
    cz=cz[0].split()[-1].split(':')[-1].split('\x93')[-1]
  
    amb=[i for i in b if 'ambulance' in i.lower()]
    if not amb:
      print(('could not find data in bulletin %s for ambulances' %(bulletin)))
      return
    amb=amb[0].split()[-1].split('\x93')[-1]

  # ~ print date,hos_capacity,hos_used,dcc_capacity,dcc_used,dchc_capacity,dchc_used,total,rtpcr,rapid,cz,amb
  
  delhi_obj=delhi_status(date,int(hos_capacity),int(hos_used),int(dcc_capacity),int(dcc_used),int(dchc_capacity),int(dchc_used),int(total),int(rtpcr),int(rapid),int(cz),int(amb))
  return delhi_obj

def delhi_parser():
  pdfs=[i for i in os.listdir('.') if i.endswith('.pdf')];pdfs.sort()
  do=[]
  for pdf in pdfs:
    try:
      #print('parsing'+pdf)
      do.append(delhi_bulletin_parser(pdf))
      if pdf=='09_08_2020.pdf':
        ds=delhi_bulletin_parser(pdf)
        ds.date=datetime.datetime(2020,9,9,0,0)
        do.append(ds); #duplicate to avoid error
      elif pdf=='07_29_2020.pdf':
        ds=delhi_bulletin_parser(pdf)
        ds.date=datetime.datetime(2020,7,30,0,0)
        do.append(ds); #duplicate to avoid error
    except:
      print(('could not parse delhi_bulletin: '+pdf))
  #manually add data for malformed bulletin days (aug 29,30 and sep 9)
  #do.append(delhi_status(datetime.datetime(2020,8,29,0,0),14143, 3966, 10143, 821, 594, 275, 22004,6597,15407,803,1371))
  #do.append(delhi_status(datetime.datetime(2020,8,30,0,0),14145, 4030, 10143, 876, 599, 336, 20437,6881,13556,820,1319))
  # ~ do.append(delhi_status(datetime.datetime(2020,6,9,0,0),8872, 4680, 285, 187, 6038, 1414, 54517,0,0,0,0))
  do.sort(key= lambda y: y.date)
  return do

def cartogram_date(date='09_20_2020',window_size=3,plot_base=False,verbose=True,ctype=''):  
  import geojson;import matplotlib.pyplot as plt;from descartes import PolygonPatch
  
  date=datetime.datetime.strptime(date,'%m_%d_%Y');orig_date=date
  date_delta=date-datetime.timedelta(days=window_size)
  states_deaths={}
  for state in state_name_to_code:
    if state.startswith(('Dadra','State Unassigned')): continue
    if ctype and  state.startswith(('Laks')): continue
    if ctype=='positivity':
      y=get_positivity(state=state)
      d_y=[i[1] for i in y if i[0]<=date and i[0]>date_delta]
      deaths_window=sum(d_y)*10 # 10 is scaling factor
    elif ctype=='confirmed':
      y=get_cases(state=state,case_type='confirmed',return_full_series=True,verbose=False)
      c_y=[i[1] for i in y if i[0]<=date and i[0]>date_delta]
      deaths_window=c_y[-1]-c_y[0] # 10 is scaling factor
    else:
      y=get_cases(state=state,case_type='deaths',return_full_series=True,verbose=False)
      d_y=[i[1] for i in y if i[0]<=date and i[0]>date_delta]
      deaths_window=d_y[-1]-d_y[0]
    states_deaths[state]=deaths_window
  #apply corrections
  # ~ states_deaths['Andhra Pradesh']=states_deaths['Andhra Pradesh']+states_deaths['Telangana']
  states_deaths['Jammu and Kashmir']=states_deaths['Jammu and Kashmir']+states_deaths['Ladakh']
  states_deaths['Uttaranchal']=states_deaths['Uttarakhand']
  
  states_deaths['Lakshadweep']=0;states_deaths['Daman and Diu']=0;states_deaths['Dadra and Nagar Haveli']=0

  # ~ states_deaths.pop('Telangana');
  states_deaths.pop('Ladakh');states_deaths.pop('Uttarakhand')
  # ~ states_deaths.pop('Dadra and Nagar Haveli and Daman and Diu')

  #now make datafile.csv for "cartogram" utility
  sk=list(states_deaths.keys());sk.sort()

  a=open('mapdata.csv','w');a.write('Region Id,Region Data,Region Name\n')
  idx=1
  for state in sk:
    info='%d,%d,%s' %(idx,states_deaths[state],state)
    a.write(info+'\n');idx+=1;
  a.close()

  #now actually make cartogram
  os.system('mv -fv mapdata.csv cartogram/')
  os.chdir('cartogram')
  # ~ cmd='time cartogram -g Indian_States_processedmap.json -a mapdata.csv'
  cmd='time cartogram -g india_telengana_processedmap.json -a mapdata.csv'
  if verbose:
    os.system(cmd)
  else:
    x=os.popen(cmd).read()
  

  #plot cartogram present in cartogram.json
  if plot_base:
    json_data=geojson.load(open('india_telengana_processedmap.json'))
  else:
    json_data=geojson.load(open('cartogram.json'))
  
  
  if plot_base: orig_date='BASEMAP'
  else: orig_date=orig_date.strftime('%b-%2d')
  
  #if doing carto with confirmed, use color for deaths
  data_dict={}  
  os.chdir('..')
  for state in state_name_to_code:
    if state.startswith(('Dadra','State Unassigned')): continue
    if ctype and  state.startswith(('Laks')): continue
    if ctype=='confirmed':
      y=get_cases(state=state,case_type='deaths',return_full_series=True,verbose=False)
      d_y=[i[1] for i in y if i[0]<=date and i[0]>date_delta]
      deaths_window=d_y[-1]-d_y[0]
    else:      
      y=get_cases(state=state,case_type='confirmed',return_full_series=True,verbose=False)
      c_y=[i[1] for i in y if i[0]<=date and i[0]>date_delta]
      deaths_window=c_y[-1]-c_y[0] # 10 is scaling factor
    data_dict[state]=deaths_window
  
  os.chdir('cartogram')
  chloropleth(data_dict=data_dict,date='',extra_title=orig_date,reverse_colormap=False,use_map='cartogram.json')
  
  #apply corrections
  
  # ~ fig=plt.figure();
  # ~ ax=fig.gca();
  # ~ BLUE='#6699cc'
  # ~ colors=plt.cm.hsv(numpy.linspace(0, 1, len(json_data['features'])))
  
  
  
  # ~ for feature,color in zip(json_data['features'],colors):
    # ~ poly=feature['geometry']
    # ~ patch=PolygonPatch(poly,fc=color,ec=color,alpha=0.5,zorder=2)
    # ~ ax.add_patch(patch);
    # ~ ax.axis('scaled');
  # ~ plt.axis('off')
  # ~ if plot_base: orig_date='BASEMAP'
  # ~ else: orig_date=orig_date.strftime('%b-%2d')
  # ~ plt.title(orig_date)
  # ~ plt.savefig(orig_date+'.png',bbox_layout='tight')
  # ~ plt.close()
  os.chdir('..')
  
  # ~ return (plt,ax,patch)

# ~ recent_elderly_vaccintion_alldoses={
# ~ 'Andaman and Nicobar Islands': 30654,
# ~ 'Andhra Pradesh': 2587408,'Assam':
def chloropleth_data():
    data=[]
    states=list(state_name_to_code.keys());states.sort()
    # ~ print(states)
    # ~ for st in ['Sikkim','Dadra and Nagar Haveli and Daman and Diu','Ladakh','Mizoram','Tripura','Nagaland','Goa']: states.remove(st)
    metric={}
    for state in tqdm.tqdm(states):
        x=get_positivity(state)
        # ~ x=get_cases(state,case_type='deaths',return_full_series=True);d,x=zip(*x);x=np.diff(x);x=moving_average(x)
        try:
          # ~ metric[state]=x[-1][1]/x[-11][1] #percent change in TPR relative to 10 days ago
          # ~ metric[state]=x[-1][1] #abs value of TPR
          # ~ metric[state]=x[-1]/x[-11] # percent change in daily deaths vs  10 days ago
          
          #elderly vacination rate on jun 2
          date,tot_persons_vaccinated,tot_sessions,firstdoses,seconddoses,males,females,covaxin,covishield,sputnik,from18to45,from45to60,over60,totdoses=zip(*vaccination_cowin_state(state))
          lastelderlyupdate=over60[-3]; #HACK as last 2 entries in covid19oindiaorg api are empty
          over60firstdoses=lastelderlyupdate*0.757; #at last update of mohfw, ~76% of total elderly doses were 1st doses
          over60pop=0
          #hack since TG didn't exist at time of 2011 census
          if state=='Telangana': over60pop=4.160e6;#print('got tg');print(over60firstdoses,over60pop)
          elif state=='Andhra Pradesh': over60pop=6.557e6
          else:
            over60pop=parse_census(state,'above60')[0]*1.356 #in all of india, 60+ grows by ~36% from 2011 to 2021
          metric[state]=over60coverage=100*(over60firstdoses/over60pop)
        
        except:
          print('failed for '+state)
          continue
        # ~ print(state)
            # ~ data.append((state,dates[i],percent_change))
  
    return metric

def vaccination_chloropleth(upto='apr29',multiple=1):  
  mar1=parse_mohfw_bulletin('bulletins/vaccination/mar01.pdf')[2]
  end=parse_mohfw_bulletin('bulletins/vaccination/'+upto+'.pdf')[2]
  
  vd={}
  failed=[]
  for state in state_name_to_code:
    try: vd[state]=int(multiple*(end[state]-mar1[state]))
    except: failed.append(state)
  print('failed for %s' %(str(failed)))
  vd0=vd.copy()
  chloropleth(vd,'','Number of 45+ vaccinated',reverse_colormap=True,no_print_error=True)
  
  vd={};failed=[]
  for state in state_name_to_code:
    try: vd[state]=100*(multiple*(end[state]-mar1[state])/parse_census(state,'above45')[0])
    except: failed.append(state)
  print('failed for %s' %(str(failed)))
  
  for i in ['Sikkim','Arunachal Pradesh','Tripura','Mizoram']:
    if i in vd: vd.pop(i)  
  vi=list(vd.items());vi.sort(key=lambda ff: ff[1])
  
  dc={}
  for i in vd:
    if i in vd0: dc[i]=(vd[i],vd0[i])
  
  chloropleth(vd,'','Percent of 45+ vaccinated(restricted set of states)',reverse_colormap=True,no_print_error=True)
  
  vd={}
  failed=[]
  for state in state_name_to_code:
    try: vd[state]=int(multiple*(end[state]-mar1[state]))
    except: failed.append(state)
  print('failed for %s' %(str(failed)))
  vd0=vd.copy()
  chloropleth(vd,'','Number of 60+ vaccinated',reverse_colormap=True,no_print_error=True)
  
  vd={};failed=[]
  for state in state_name_to_code:
    try: vd[state]=100*(multiple*(end[state]-mar1[state])/parse_census(state,'above60')[0])
    except: failed.append(state)
  print('failed for %s' %(str(failed)))
  
  for i in ['Sikkim','Arunachal Pradesh','Tripura','Mizoram']:
    if i in vd: vd.pop(i)  
  vi2=list(vd.items());vi2.sort(key=lambda ff: ff[1])
  
  dc={}
  for i in vd:
    if i in vd0: dc[i]=(vd[i],vd0[i])
  
  chloropleth(vd,'','Percent of 60+ vaccinated(restricted set of states)',reverse_colormap=True,no_print_error=True)
  # ~ vi2=list(vd.items());vi2.sort(key=lambda ff: ff[1])

  vd={};failed=[]
  for state in state_name_to_code:
    try: vd[state]=100*(end[state]/parse_census(state,'tot_persons'))
    except: failed.append(state)
  print('failed for %s' %(str(failed)))
  
  for i in ['Sikkim','Arunachal Pradesh','Tripura']:
    if i in vd: vd.pop(i)  
  chloropleth(vd,'','Percent of total pop. vaccinated(restricted set of states)',reverse_colormap=True,no_print_error=True)
  vi3=list(vd.items());vi3.sort(key=lambda ff: ff[1])
  return vi,vi2,vi3
  
def norm_cmap(values, cmap='YlGn', vmin=None, vmax=None):
  import matplotlib.pyplot as plt
  from matplotlib.colors import Normalize
  mn = vmin or min(values)
  mx = vmax or max(values)
  norm = Normalize(vmin=mn, vmax=mx)
  n_cmap = plt.cm.ScalarMappable(norm=norm, cmap=cmap)
  return n_cmap
  
  
def chloropleth(data_dict={},date='',extra_title='',reverse_colormap=False,use_map='',cmap='',colorbar_label='',no_print_error=False):
  from  matplotlib.colors import LinearSegmentedColormap
  import matplotlib.colors as colors
  import matplotlib.cm as cm
  from descartes import PolygonPatch;import matplotlib.pyplot as plt;import geojson
  cdict={'red': ((0,0,0),(0.5,1,1),(1,0.8,0.8)),
          'green': ((0,0.8,0.8),(0.5,1,1),(1,0,0)),
          'blue' : ((0,0,0),(0.5,1,1),(1,0,0))
  }
  
  if not cmap:
    cmap=LinearSegmentedColormap.from_list('',["g", "y", "r"], N=256) 
    if reverse_colormap: cmap=LinearSegmentedColormap.from_list('rg',["r", "y", "g"], N=256) 
    cmap=norm_cmap(data_dict.values(),cmap)
  jsonfile='india_state.json'
  if use_map and use_map.endswith('json'): jsonfile=use_map
  #jsonfile='india_telengana.geojson'
  json_data=geojson.load(open(jsonfile))

  fig=plt.figure();
  ax=fig.gca();
  #colors=plt.cm.hsv(numpy.linspace(0, 1, len(json_data['features'])))
  
  #for feature,color in zip(json_data['features'],colors):
  for feature in json_data['features']:
    poly=feature['geometry']
    if 'gana' in jsonfile or 'cartogram' in jsonfile:
      name=feature.properties['NAME_1']
    else:
      name=feature.properties['ST_NM']
    if name in data_dict:
        data_value=data_dict[name]
        color=cmap.to_rgba(data_value)
        # ~ color=cmap(data_value)
        # ~ if data_value<0: #green
            # ~ color=[0,np.abs(data_value),0]
        # ~ else: #red
            # ~ color=[np.abs(data_value),0,0]
    else:
        if not no_print_error:
          print('Feature with name %s was not in data_dict' %(name))
        continue
    patch=PolygonPatch(poly,fc=color,ec=color,alpha=0.5,zorder=2)
    ax.add_patch(patch);
    ax.axis('scaled');
  plt.axis('off')
  
  orig_date=''
  if date: orig_date=date.strftime('%b-%d')
  if extra_title: 
    if orig_date: orig_date+=' '
    orig_date+=extra_title
  plt.title(orig_date)
  
  #COLORBAR
  from mpl_toolkits.axes_grid1 import make_axes_locatable 
  divider = make_axes_locatable(ax)
  cax = divider.append_axes('right', size='5%', pad=0.05)
  # ~ fig.colorbar(cmap,cax=cax, orientation='vertical')
  if colorbar_label:
    fig.colorbar(cmap,cax=cax, orientation='vertical',label=colorbar_label)
  else:
    fig.colorbar(cmap,cax=cax, orientation='vertical')
  # ~ import matplotlib.colorbar;  matplotlib.colorbar.ColorbarBase(ax=ax,values=sorted(data_dict.values()),orientation='vertical')
  
  fig.tight_layout()
  pylab.legend()
  
  # ~ plt.savefig(TMPDIR+orig_date+'.png',bbox_layout='tight')
  plt.savefig(TMPDIR+orig_date+'.png')
  print('saved to %s.png' %(orig_date))

def cartogram(window_size=7,ctype=''):
  # ~ d1=datetime.date(2020,5,1);d2=datetime.date(2020,9,23);delta=d2-d1
  d2=datetime.date(2021,3,4);d1=datetime.date(2020,9,28);delta=d2-d1
  dates=[(d1 + datetime.timedelta(days=i)) for i in range(1,delta.days + 1)]
  dates=dates[::window_size]
  for date in dates:
    str_date=date.strftime('%m_%d_%Y')
    print(('DATE: '+str_date))
    x=cartogram_date(str_date,window_size=window_size,verbose=False,ctype=ctype)
  
def karnataka_analysis(district='Bengaluru Urban',xlim='',plot_days=''):
  #hos_capacity='';hos_used='';dcc_capacity='';dcc_used='';dchc_capacity='';dchc_used='';
  # ~ hos_util=0;dcc_util=0;dchc_util=0
  # ~ total='';rtpcr='';rapid='';
  # ~ cz='';amb='';date=''
  # ~ import pylab

  y=''
  if district=='Total':
    y=get_cases(state='Karnataka',case_type='deaths',return_full_series=True,verbose=False)
    y2=get_cases(state='Karnataka',case_type='active',return_full_series=True,verbose=False)
  elif district=='RoK':
    y=get_cases(state='Karnataka',case_type='deaths',return_full_series=True,verbose=False)
    y2=get_cases(state='Karnataka',case_type='active',return_full_series=True,verbose=False)
    y0=get_cases_district(state='Karnataka',district='Bengaluru Urban',case_type='deaths_delta')
    y20=get_cases_district(state='Karnataka',district='Bengaluru Urban',case_type='active')
    icu=karnataka_parse_icu_clipping();
    ic=[(i.date,i.icu) for i in icu if i.district=='Total']
    ic0=ic
    ic2=[(i.date,i.icu) for i in icu if i.district=='BengaluruUrban']
    print(len(ic),len(ic2))

  else:
    y=get_cases_district(state='Karnataka',district=district,case_type='deaths_delta')
    y2=get_cases_district(state='Karnataka',district=district,case_type='active')
  icu=karnataka_parse_icu_clipping();ic=[(i.date,i.icu) for i in icu if i.district==district.replace(' ','')]
  # ~ print ic

  if district=='Total':
    d=moving_average(numpy.diff([i[1] for i in y]))
    #dates=pylab.date2num([i[0] for i in y][5:])
    dates=pylab.date2num([i[0] for i in y][1:])
    a=[i[1] for i in y2]
    dates3=pylab.date2num([i[0] for i in y2])
  elif district=='RoK':
    d=moving_average(numpy.diff([i[1] for i in y]))
    d1=moving_average([i[1] for i in y0])
    d=d[-1*len(d1):]
    d=np.array(d)-np.array(d1)
    #dates=pylab.date2num([i[0] for i in y][5:])
    dates=pylab.date2num([i[0] for i in y0])
    a=[i[1] for i in y2]
    a1=[i[1] for i in y20]
    a=a[-1*len(a1):]
    a=np.array(a)-np.array(a1)
    dates3=pylab.date2num([i[0] for i in y20])
    ic=[(i[0],i[1]-j[1]) for i,j in zip(ic0,ic2)]


  else:
    d=moving_average([i[1] for i in y])
    #dates=pylab.date2num([i[0] for i in y][4:])
    dates=pylab.date2num([i[0] for i in y])
    a=[i[1] for i in y2]
    dates3=pylab.date2num([i[0] for i in y2])
    
  dates2=pylab.date2num([i[0] for i in ic])
  ic=[i[1] for i in ic]


  print('plotting icu vs deaths') 

  plot2(dates2,ic,dates,d,label1=district+' ICU beds',label2=district+' daily deaths',state='',plot_days=plot_days)
#  sp,ax=pylab.subplots()
#  import matplotlib.dates as mdates
#  locator = mdates.AutoDateLocator(minticks=3, maxticks=7)
#  formatter = mdates.ConciseDateFormatter(locator)
#  ax.xaxis.set_major_locator(locator)
#  ax.xaxis.set_major_formatter(formatter) 
#
#  #pylab.clf()
#  color = 'tab:blue'
#  ax.set_xlabel('Date')
#  ax.set_ylabel('ICU beds',color=color)
#  ax.plot_date(dates2,ic,color=color,label=district+' ICU beds')
#  if xlim: ax.set_xlim(xlim)
#  ax.tick_params(axis='y', labelcolor=color)  
#
#  ax2=ax.twinx()
#  color = 'tab:red'
#  ax2.set_ylabel('Daily deaths (7-day MA)',color=color)
#  ax2.plot_date(dates,d,color=color,label=district+' daily deaths')
#  ax2.tick_params(axis='y', labelcolor=color)
#
#  sp.tight_layout()
#
#  title=district+' ICU use vs daily deaths'
#  pylab.title(title);
#  ax2.legend(loc='upper right');
#  ax.legend(loc='upper left');
#  pylab.legend();
#  pylab.show()
#  pylab.savefig(TMPDIR+'karnataka_'+district+'_icu_vs_daily_deaths.jpg');pylab.close()
  
  print('plotting icu vs actives') 
  plot2(dates2,ic,dates3,a,label1=district+' ICU beds',label2=district+' active cases',color2='orange',state='',plot_days=plot_days)
#  sp,ax=pylab.subplots()
#  locator = mdates.AutoDateLocator(minticks=3, maxticks=7)
#  formatter = mdates.ConciseDateFormatter(locator)
#  ax.xaxis.set_major_locator(locator)
#  ax.xaxis.set_major_formatter(formatter) 
#
#  #pylab.clf()
#  color = 'tab:blue'
#  ax.set_xlabel('Date')
#  ax.set_ylabel('ICU beds',color=color)
#  ax.plot_date(dates2,ic,color=color,label=district+' ICU beds')
#  ax.tick_params(axis='y', labelcolor=color)  
#
#  ax2=ax.twinx()
#  color = 'tab:orange'
#  ax2.set_ylabel('Active Cases',color=color)
#  ax2.plot_date(dates3,a,color=color,label=district+' active cases')
#  ax2.tick_params(axis='y', labelcolor=color)
#
#  sp.tight_layout()
#
#  title=district+' ICU use vs active cases'
#  pylab.title(title);  
#  ax2.legend(loc='lower right');
#  ax.legend(loc='lower left');
#  pylab.legend();
  #pylab.show()
#  pylab.savefig(TMPDIR+'karnataka_'+district+'_icu_vs_actives.jpg');pylab.close()
  if district=='RoK':
      return (dates2,ic,ic0,ic2,dates,d)


def parse_bbmp_beds():
  base='bed_status/bbmp/'  
  if not os.path.exists(base): print((base+' not found'));return
  htm=[i for i in os.listdir(base) if i[0].isdigit() and i.endswith(('.htm','.html'))];htm.sort()
  from bs4 import BeautifulSoup
  bed_availability={}
  import tqdm;pbar=tqdm.tqdm(htm,desc='parsing')
  for i in pbar:
    pbar.set_description('parsing '+i)

    date=datetime.datetime.strptime(i.split('.')[0],'%d_%m')
    if not date in bed_availability: bed_availability[date]={}

    fname=base+i.split('.')[0]+'_files/saved_resource.html'
    soup=BeautifulSoup(open(fname).read(),'lxml')

    t=soup('table',attrs={'id':'PrivateQuota'})[0]

    private_beds=int(t('tr')[1]('td')[-1].text.replace(',',''))
    private_ccc=int(t('tr')[2]('td')[-1].text.replace(',',''))
    home_isolation=int(t('tr')[3]('td')[-1].text.replace(',',''))

    t=soup('table',attrs={'id':'GovernmentHospitalsDetail'})[0]
    val=[i.text.replace(',','') for i in t('tr')[-1]('td')]
    hdu=int(val[3]);icu=int(val[4]);vent=int(val[5])
    hdu_occ=int(val[8]);icu_occ=int(val[9]);vent_occ=int(val[10])

    for t in soup('table',attrs={'id':'GovernmentMedical'})[:-1]:
      val=[i.text.replace(',','') for i in t('tr')[-1]('td')]
      hdu+=int(val[3]);icu+=int(val[4]);vent+=int(val[5])
      hdu_occ+=int(val[8]);icu_occ+=int(val[9]);vent_occ+=int(val[10])
    bed_availability[date]={'hdu':(hdu,hdu_occ),'icu':(icu,icu_occ),'vent':(vent,vent_occ),'home':home_isolation,'private':private_beds}

  print('-------------\nDATE\tICU\tVent.\tHDU\tHome.Isol.\n')
  x=bed_availability;xk=list(x.keys());xk.sort()
  for i in xk:
    date=i.strftime('%d-%m')
    info='%s\t%s\t%s\t%s\t%s' %(date,x[i]['icu'][1],x[i]['vent'][1],x[i]['hdu'][1],x[i]['home'])
    print(info)

  return bed_availability
  
def parse_chennai_beds(print_district='Chennai'):
  base='bed_status/chennai/'  
  if not os.path.exists(base): print((base+' not found'));return
  
  htm=[i for i in os.listdir('bed_status/chennai/') if i[0].isdigit() and i.endswith(('.htm','.html'))];htm.sort()
  from bs4 import BeautifulSoup
  bed_availability={}
  import tqdm;pbar=tqdm.tqdm(htm,desc='parsing')
  for i in pbar:
    # ~ print 'parsing '+i
    pbar.set_description('parsing '+i)

    date=datetime.datetime.strptime(i.split('-')[0],'%d_%m')
    if not date in bed_availability: bed_availability[date]={}
    
    soup=BeautifulSoup(open(base+i).read(),'lxml')
    rows=soup('tr',attrs={'role':'row'})[2:]

    for row in rows:
      entries=row('td')
      district=entries[0].text
      if district not in bed_availability[date]: bed_availability[date][district]={}
      
      hospital_name=entries[1].text
      # ~ covid_beds=int(entries[2].text)
      # ~ covid_beds_used=int(entries[3].text)
      oxygen_beds=int(entries[5].text)
      oxygen_beds_used=int(entries[6].text)
      # ~ non_oxygen_beds=int(entries[8].text)
      # ~ non_oxygen_beds_used=int(entries[9].text)
      icu_beds=int(entries[11].text)
      icu_beds_used=int(entries[12].text)
      ventilator_beds=int(entries[14].text)
      ventilator_beds_used=int(entries[15].text)

      
      if 'oxygen' in bed_availability[date][district]:
        bed_availability[date][district]['oxygen']=(bed_availability[date][district]['oxygen'][0]+oxygen_beds,bed_availability[date][district]['oxygen'][1]+oxygen_beds_used)
      else:
        bed_availability[date][district]['oxygen']=(oxygen_beds,oxygen_beds_used)
      if 'icu' in bed_availability[date][district]:
        bed_availability[date][district]['icu']=(bed_availability[date][district]['icu'][0]+icu_beds,bed_availability[date][district]['icu'][1]+icu_beds_used)
      else:
        bed_availability[date][district]['icu']=(icu_beds,icu_beds_used)
      if 'ventilator' in bed_availability[date][district]:
        bed_availability[date][district]['ventilator']=(bed_availability[date][district]['ventilator'][0]+ventilator_beds,bed_availability[date][district]['ventilator'][1]+ventilator_beds_used)
      else:
        bed_availability[date][district]['ventilator']=(ventilator_beds,ventilator_beds_used)
  # ~ bed_availabilities=[]
  # ~ for date in bed_availability:
    # ~ ba=generic_bed_availability(bed_availability[date],date)
  print(('-----------\n'+print_district+':\nDATE\t\tICU\t\tVent.\t\tOxygen'))
  x=bed_availability;xk=list(x.keys());xk.sort()
  for i in xk:
    date=i.strftime('%d-%m')
    info='%s\t\t%s/%s\t\t%s/%s\t\t%s/%s' %(date,x[i][print_district]['icu'][1],x[i][print_district]['icu'][0],x[i][print_district]['ventilator'][1],x[i][print_district]['ventilator'][0],x[i][print_district]['oxygen'][1],x[i][print_district]['oxygen'][0])
    print(info)
  return bed_availability
      
    
def delhi_analysis(do='',use_moving_average=True,plot_days=''):
  #hos_capacity='';hos_used='';dcc_capacity='';dcc_used='';dchc_capacity='';dchc_used='';
  # ~ hos_util=0;dcc_util=0;dchc_util=0
  # ~ total='';rtpcr='';rapid='';
  # ~ cz='';amb='';date=''
  # ~ import pylab
  is_dch=True
  if not do:
    # ~ do=delhi_parse_json()
    do=delhi_parse_csv()
    is_dch=False
  dates=[i.date for i in do]

  hos_used=[i.hos_used for i in do]
  # ~ dhc_used=[i.dchc_used for i in do]  
  # ~ dcc_used=[i.dcc_used for i in do]
  hos_cap=[i.hos_capacity for i in do]
  
  dates0=dates
  dates=pylab.date2num(dates)
  
  # ~ tot=[i.total for i in do]
  # ~ r=[i.rapid for i in do]
  # ~ rtpcr=[i.rtpcr for i in do]
  # ~ rp=numpy.float64(r)/numpy.float64(tot)

  # ~ cz=[i.cz for i in do]

  actives=get_cases(state='Delhi',case_type='active',return_full_series=True,verbose=True)
  deaths=get_cases(state='Delhi',case_type='deaths',return_full_series=True,verbose=True)
  dates2=[i[0] for i in actives]
  dates3=[i[0] for i in deaths]
  actives=[i[1] for i in actives]
  deaths=numpy.diff([i[1] for i in deaths ])
  deaths=deaths[-1*len(dates):]
   
  if len(actives)!=len(hos_used): actives=actives[-1*len(hos_used):]  

  # ~ hp=100*(numpy.float64(hos_used)/numpy.float64(actives))
  hc=100*(numpy.float64(hos_used)/numpy.float64(hos_cap))
  
  if use_moving_average: 
    hos_used=moving_average(hos_used)
    hos_cap=moving_average(hos_cap)
    actives=moving_average(actives)
    deaths=moving_average(deaths)
  
  if plot_days:
      actives=actives[-1*plot_days:]
      hos_used=hos_used[-1*plot_days:];      hos_cap=hos_cap[-1*plot_days:];hc=hc[-1*plot_days:]
      deaths=deaths[-1*plot_days:]
      dates=dates[-1*plot_days:]
      dates2=dates2[-1*plot_days:]
      dates3=dates3[-1*plot_days:]  
      plot2(dates,hos_used,dates2,actives,label1='Hospital beds used',label2='Active cases',color2='orange',state='Delhi')
      plot2(dates,hos_used,dates3,deaths,label1='Hospital beds used',label2='Daily Deaths',color2='red',state='Delhi')
      if is_dch:
        plotex(dates,hos_used,dates,hos_cap,label='beds used',label2='DCH Bed Capacity',color2='red',state='Delhi')
        plot2(dates,hos_used,dates,hc,label1='DCH beds used',label2='Percentage capacity used',color2='red',state='Delhi')
  print(len(hos_used),len(hos_cap))
  # ~ return (dates,deaths)
  return (dates0,hos_used,hos_cap,deaths)
  
def update_data_files(extra=False):
  urls=['https://api.covid19india.org/states_daily.json','https://api.covid19india.org/state_test_data.json','https://api.covid19india.org/csv/latest/tested_numbers_icmr_data.csv','https://api.covid19india.org/csv/latest/vaccine_doses_statewise.csv','https://api.covid19india.org/data.json']
  
  # ~ if extra: urls.extend(['https://api.covid19india.org/v4/data-all.json'])
  if extra: urls.extend(['https://api.covid19india.org/csv/latest/districts.csv'])
  for i in urls:
    filename=os.path.split(i)[1]
    if os.path.exists(filename):
      os.remove(filename)
    cmd='wget -q "'+i+'" -O "'+filename+'"';
    print(cmd)
    os.system(cmd);

class kerala_community_tr():
  date='';percent_unknown=''
  def __init__(self,date,percent_unknown):
    self.percent_unknown=percent_unknown
    self.date=date

class delhi_status():
  hos_capacity='';hos_used='';dcc_capacity='';dcc_used='';dchc_capacity='';dchc_used='';
  hos_util=0;dcc_util=0;dchc_util=0
  total='';rtpcr='';rapid='';
  cz='';amb='';date=''
  def __init__(self,date,hos_capacity,hos_used,dcc_capacity,dcc_used,dchc_capacity,dchc_used,total,rtpcr,rapid,cz,amb):
    
    self.date,self.hos_capacity,self.hos_used,self.dcc_capacity,self.dcc_used,self.dchc_capacity,self.dchc_used,self.total,self.rtpcr,self.rapid,self.cz,self.amb=date,hos_capacity,hos_used,dcc_capacity,dcc_used,dchc_capacity,dchc_used,total,rtpcr,rapid,cz,amb
    if self.hos_used: self.hos_util=100*(self.hos_used/float(self.hos_capacity))
    if self.dchc_used: self.dchc_util=100*(self.dchc_used/float(self.dchc_capacity))
    if self.dcc_used: self.dcc_util=100*(self.dcc_used/float(self.dcc_capacity))
  def info(self):
    info=''
    if self.date: info='On date: %s\n' %(datetime.datetime.strftime(self.date,'%d/%m/%Y'))
    info+='\tHospital: %d/%d (%.1f percent)\n' %(self.hos_used,self.hos_capacity,self.hos_util)
    info+='\tDCHC: %d/%d (%.1f percent)\n'  %(self.dchc_capacity,self.dchc_used,self.dchc_util)
    info+='\tDCCC: %d/%d (%.1f percent)\n'%(self.dcc_capacity,self.dcc_used,self.dcc_util)
    info+='Tests:\n\tTotal: %d\n' %(self.total)
    if self.rtpcr:
      info+='\tRTPCR: %d\n\tRapid: %d' %(self.rtpcr,self.rapid)
    info+='Misc:\n\tContainment Zones: %d\n\tAmbulance calls: %d' %(self.cz,self.amb)
    print(info)
  def csv_row(self):
    row=[self.date,str(self.hos_capacity),str(self.hos_used),str(self.dcc_capacity),str(self.dcc_used),str(self.dchc_capacity),str(self.dchc_used),str(self.total),str(self.rtpcr),str(self.rapid),str(self.cz),str(self.amb)]
    return row
    
  
#class meant to represent Odisha's fatality data (in a very specific format)
class fatality():
  date='';age='';gender='';district='';comorbidity=[];comorb_string=''
  def __init__(self,fatality_string='',date=''):
    self.date_string=date
    self.date=datetime.datetime.strptime(self.date_string,'%Y-%m-%d')
    ss='.'.join(fatality_string.split('.')[1:]).strip()
    if ss.endswith('.'):ss=ss[:-1]
    # bhub. is in khorda district.
    replacements = {"district ": "",'district.':'','Bhubaneswar':'Khorda','-year':' year'}      
    for i in replacements: ss=ss.replace(i,replacements[i])
    ss="".join([replacements.get(c, c) for c in ss])  
    ss=ss.strip().lower();

    age_gender=ss.split('of')[0].strip()
    age=age_gender.split(' ')[age_gender.split(' ').index('year')-1]
    if age.isdigit(): self.age=int(float(age))
    else:             print(('for %s, could not parse age: %s from age_gender string: %s' %(fatality_string,age,age_gender)))
    self.gender=age_gender.split(' ')[-1]
      
    if 'who' in ss: #has comorbidity
      district=ss.split('who')[0]
      if 'of' not in district:
        print(('for %s, could not district: %s from ss: %s' %(fatality_string,district,ss)))
      else:
        district=district.split('of')[1].strip()
      self.district=district
      assert(len(ss.split('who'))==2); #there should be only 1 "who" in statement
      comorb_string=ss.split('who')[1].strip()
      replacements = {"was also suffering from ": "",'expired due to ':'','and':',','&':','}
      for i in replacements: comorb_string=comorb_string.replace(i,replacements[i])
      self.comorb_string=comorb_string;comorbidity=[]
      for i in comorb_string.split(','): comorbidity.append(i.strip())
      self.comorbidity=comorbidity
    else: #no cormobidity
      self.district=ss.split('of')[1].strip()
    self.district=self.district.replace('district','').strip()
  def info(self):
    info='Age:\t\t%d\nGender:\t\t%s\nDistrict:\t%s\nDate:\t\t%s' %(self.age,self.gender,self.district,self.date)
    if self.comorbidity: info+='\nComorbidity:\t%s' %(','.join(self.comorbidity))
    else: info+='\nComorbidity:\t\tNONE' 
    print(info)


  
class generic_fatality():
  district='';patient_number='';age='';gender='';origin='';comorbidities='';
  date_of_detection='';date_of_admission='';date_of_death='';
  date_of_reporting=''
  detection_admission_interval=''
  detection_death_interval=''
  admission_death_interval=''
  death_reporting_interval=''
  def __init__(self,district,patient_number,age,gender,origin,comorbidity,date_of_admission,date_of_death,bulletin_date,state='Karnataka'):
    self.district=district
    if patient_number:
      self.patient_number=int(patient_number.replace('n',''))
    age=age.lower().replace('yrs','').replace('y','');#workaround for typos in bulletin
    self.age=int(float(age))
    self.gender=gender
    self.origin=origin
    if state=='Karnataka':
      self.comorbidities=comorbidity.split(',')
    else:
      self.comorbidities=comorbidity.split(' /')
    if state=='Karnataka':
      
      self.date_of_detection=karnataka_map_patient_no_to_date(self.patient_number,global_karnataka_case_series)
    
    self.date_of_admission=date_of_admission
    self.date_of_death=date_of_death
    self.date_of_reporting=bulletin_date
    # ~ print self.date_of_reporting
    
    # ~ self.hospital_type=hospital_type

    if self.date_of_admission==datetime_doa_marker: #means patient was dead on arrival
      self.admission_death_interval=-1
      if self.date_of_detection:
        self.detection_admission_interval=(self.date_of_death-self.date_of_detection).days    
    else:
      if self.date_of_admission:
        if self.date_of_death:
          self.admission_death_interval=(self.date_of_death-self.date_of_admission).days
        if self.date_of_detection:
          self.detection_admission_interval=(self.date_of_admission-self.date_of_detection).days    
    if self.date_of_detection:
      if self.date_of_death:
        self.detection_death_interval=(self.date_of_death-self.date_of_detection).days
    if self.date_of_reporting:
      try:
        self.death_reporting_interval=(self.date_of_reporting-self.date_of_death).days
      except:
        print(('error calculating death_reporting_interval with dor: '+str(self.date_of_reporting)+' and dod '+str(self.date_of_death)))
      
  def info(self):
    info_str=''
    if self.patient_number: info_str+='P.no %d ' %(self.patient_number)
    info_str+='District: %s Age: %d Gender: %s Origin: %s\n' %(self.district,self.age,self.gender,self.origin)
    info_str+='Comorbidities: %s\n' %(' '.join(self.comorbidities))
    dod='N/A'
    if self.date_of_detection:
      dod=self.date_of_detection.strftime('%d/%m/%Y')
    doa='';dor='';dode=''
    if self.date_of_admission: doa=self.date_of_admission.strftime('%d/%m/%Y')
    if self.date_of_reporting: dor=self.date_of_reporting.strftime('%d/%m/%Y')
    if self.date_of_death: dode=self.date_of_death.strftime('%d/%m/%Y')
    info_str+='Detected: %s Admitted: %s Died: %s Reported: %s\n' %(dod,doa,dode,dor)
    if self.admission_death_interval: info_str+='admission_death_interval: %d\n' %(self.admission_death_interval)
    if self.detection_admission_interval: info_str+='detection_admission_interval: %d\n' %(self.detection_admission_interval)    
    if self.detection_death_interval: info_str+='detection_death_interval: %d\n' %(self.detection_death_interval)
    if self.death_reporting_interval: info_str+='death_reporting_interval: %d' %(self.death_reporting_interval)
    print((info_str.strip()))
  def csv_row(self):
    doa=self.date_of_admission
    dode=self.date_of_detection    
    dod=self.date_of_death
    dor=self.date_of_reporting
    if dode: dode=dode.date()
    if doa: doa=doa.date()
    if dod: dod=dod.date()
    if dor: dor=dor.date()
    row_objects=[self.patient_number,self.district,self.age,self.gender,self.origin,dode,doa,dod,dor]
    if self.comorbidities: row_objects.extend(self.comorbidities)
    return row_objects
    
    

class generic_icu_usage():
  date='';district='';icu='';ventilator='';state=''
  def __init__(self,bulletin_date,district_name,icu_usage,ventilator_usage='',state='Kerala'):
    self.date=bulletin_date
    self.district=district_name
    self.icu=icu_usage
    if ventilator_usage: self.ventilator=ventilator_usage
    self.state=state
    
  def info(self):
    info_str='In %s,  district: %s on %s, icu_usage: %d' %(self.state,self.district,self.date.strftime('%d-%m-%Y'),self.icu)
    if self.ventilator: info_str+=' ventilator: '+str(self.ventilator)
    print(info_str)
class karnataka_discharge():
  patient_number='';date_of_detection='';date_of_discharge='';
  district='';detection_discharge_interval=0
  def __init__(self,district_name,patient_number,bulletin_date):    
    self.date_of_discharge=bulletin_date
    self.district=district_name
    if ',' in patient_number: patient_number=patient_number.replace(',','').strip()
    self.patient_number=int(patient_number.replace('n',''))
    self.date_of_detection=karnataka_map_patient_no_to_date(self.patient_number,global_karnataka_case_series)
    try:
      self.detection_discharge_interval=(self.date_of_discharge-self.date_of_detection).days
    except:
      # ~ print 'error in calculating detection-discharge interval between '+str(self.date_of_discharge)+' and '+str(self.date_of_detection)
      # ~ self.info()
      self.district='ERROR'
  def info(self):
    info_str='P.no: %d of district: %s\nDetected: %s\tDischarges: %s\nDetection-Discharge Interval: %d' %(self.patient_number,self.district,self.date_of_detection,self.date_of_discharge,self.detection_discharge_interval)
    print(info_str)


def helper_list_value_occurences(l=[],normed=False,sort=False): #make frequency distribution of list't values
  values=list(set(l));values.sort()
  d={};freq=[]
  for i in l:
    if i in d: d[i]+=1
    else: d[i]=1
  if normed:
    freq.extend([100*(d[i]/float(len(l))) for i in values])
  else:
    freq.extend([d[i] for i in values])
  # ~ return (values,freq)
  
  # ~ z=zip(freq,values)
  z=list(zip(values,freq))
  if sort: z.sort()
  return z

def wb_parse_bulletin(bulletin='WB_DHFW_Bulletin_16th_SEPTEMBER_REPORT_FINAL.pdf'):
  cmd='pdftotext -layout "'+bulletin+'" tmp.txt';os.system(cmd)
  b=[i.strip() for i in open('tmp.txt').readlines() if i.strip()]

  tot_covid_beds=int([i for i in b if 'armark' in i][0].split()[-1].replace(',',''))
  icu=int([i for i in b if 'ICU' in i][0].split()[-1].replace(',',''))
  vent=int([i for i in b if 'entilat' in i][0].split()[-1].replace(',',''))
  occupancy_pc=float([i for i in b if 'ccupa' in i][0].split()[-1].replace('%',''))
  occupied_beds=int(0.01*occupancy_pc*tot_covid_beds)

  gov_quan=int([i for i in b if 'in Govt. Qua' in i][0].split()[-1].replace(',',''))
  home_quan=int([i for i in b if 'in Home Qua' in i][0].split()[-1].replace(',',''))

  date=[i for i in b if 'ulletin' in i.lower()][0].split('\xe2\x80\x93')[-1].split('-')[-1].strip()

  return (date,occupied_beds,tot_covid_beds,icu,vent,home_quan+gov_quan)
  
def moving_average(input_array=[],window_size=7,index_to_do_ma=1,centered=True):
  x=input_array
  if centered:
    half_window=int(window_size/2)
    x2=[]
    # ~ for index in range(half_window,len(x)-half_window-1):
    for index in range(len(x)):
      left=index-half_window
      if left<0: left=0
      right=index+half_window
      x2.append(float(sum(x[left:right]))/len(x[left:right]))
    return x2
    
  if type(input_array[0])==tuple:
    x=[i[index_to_do_ma] for i in input_array]
    dates=[i[0] for i in input_array]
    x2=numpy.convolve(x, numpy.ones((window_size,))/window_size, mode='valid')
    x2=list(x[:window_size-1])+list(x2)
    return list(zip(dates,x2))
  else:
    x=numpy.convolve(input_array, numpy.ones((window_size,))/window_size, mode='valid')
    x2=list(input_array[:window_size-1])+list(x)
    return x2 
   

def odisha_parser():
      
  b=[i.strip() for i in open('odisha_fatalities_parsed.txt').readlines() if i.strip() and i.strip().split('.')[0].isdigit()]
  #have data from July-11 to Sep-8
  d1=datetime.date(2020,7,11);d2=datetime.date(2020,9,8);delta=d2-d1
  dates=[(d1 + datetime.timedelta(days=i)).strftime('%Y-%m-%d') for i in range(delta.days + 1)]
  dates.reverse();  #raw data starts with last date first

  fatalities=[]

  dates_index=0;  current_index=0; #current_index is index of entry on specific date
  for i in b:    
    entry_index=int(i.split('.')[0].strip())
    ft=''
    #means different date
    if entry_index<current_index:    dates_index+=1;
    try: date=dates[dates_index]
    except:
      print((dates_index, i))
    fatalities.append(fatality(i,date))
    current_index=entry_index
  return fatalities


# ~ def karnataka_map_patient_no_to_date(patient_no=1,case_series=[]):
  # ~ date_of_case=''

  # ~ #need this for function that calculates which date a P. no. falls on
  # ~ if not case_series:
    # ~ case_series=get_cases(state='Karnataka',case_type='confirmed',return_full_series=True,verbose=False)
    
  # ~ for i in case_series:
    # ~ if patient_no>i[1]: continue
    # ~ else:               date_of_case=i[0];break;
  # ~ return date_of_case

# ~ def karnataka_map_patient_no_to_date2(patient_no=1,case_series=[]):
def karnataka_map_patient_no_to_date(patient_no=1,case_series=''):
  date=''
  try:
    date=global_karnataka_case_date_series[numpy.searchsorted(global_karnataka_case_number_series,patient_no)]
  except:
    # ~ print 'could not find date for patient no: '+str(patient_no)
    pass
  return date

def tamil_nadu_auto_cases_actual(bulletin=''):
  #get date first
  date=tamil_nadu_bulletin_parser(bulletin,return_date=True)\
  #check pg6 infact contains breakup of cases
  cmd='pdftotext -nopgbrk -layout "'+bulletin+'" -f 6 -l 6 tmp.txt';os.system(cmd)
  b=[i.strip() for i in open('tmp.txt').readlines() if i.strip()][0].strip()
  if not b.startswith('Age and Sex distribution'): print('Page 6 of %s did not start with "Age and Sex distribution"..' %(bulletin));return
  cmd='pdftotext -nopgbrk -layout "'+bulletin+'" -f 6 -l 6 -x 355 -y 0 -W 400 -H 700 tmp.txt';os.system(cmd)
  b=[i.strip() for i in open('tmp.txt').readlines() if i.strip()]
  index=0
  for i in b:
    if 'Male' in i: break
    else: index+=1
  rest=b[index+1:]
  if not rest: print('could not find the text with "male" in parsing '+bulletin);return
  cases=rest[0]
  if cases.isnumeric(): cases=int(cases)
  else: print('60+ cases found in %s was %s which is not numeric' %(bulletin,cases))
  
  a=open('tmp.csv','a')
  a.write('%s,%s\n' %(date.strftime('%d-%m'),str(cases)))
  a.close()
  
  return cases
  
def tamil_nadu_auto_cases(bulletin='',noexc=False):
  if noexc:
    return tamil_nadu_auto_cases_actual(bulletin)
  else:
    try: return tamil_nadu_auto_cases_actual(bulletin)
    except: print('unable to get 60+ cases info from %s' %(bulletin))
  

def karnataka_parse_vaccination(multiple=1.15,plot=False):
  r=csv.reader(open('csv_dumps/karnataka_vaccination.csv'))
  info=[]
  for i in r: info.append(i)
  info=info[1:]
  out=[]
  for i in info:
    date,a60vaccinated,from45to60vaccinated=i
    date=datetime.datetime.strptime(date+'/2021','%d/%m/%Y')
    out.append((date,int(a60vaccinated),int(from45to60vaccinated)))
  
  tot=float(parse_census('ka','above60')[0])*multiple
  dates,v,v2=zip(*out);
  v=np.int_(moving_average(v,window_size=7));  v2=np.int_(moving_average(v2,window_size=7))
  percent_elderly_vaccinated=(v/tot)*100;  
  tot=float(parse_census('ka','above45')[0])*multiple
  percent_over45_vaccinated=((v+v2)/tot)*100
  out2=list(zip(dates,v,v2,percent_elderly_vaccinated,percent_over45_vaccinated))
  
  if plot:
    sp,ax=pylab.subplots()
    locator = mdates.AutoDateLocator(minticks=3, maxticks=7);formatter = mdates.ConciseDateFormatter(locator)
    ax.xaxis.set_major_locator(locator);    ax.xaxis.set_major_formatter(formatter) 

    ax.set_xlabel('Date')
    ax.set_ylabel('Percent of 60+ vaccinated in KA  (7-day MA)')
    ax.plot_date(pylab.date2num(dates),percent_elderly_vaccinated,label='Percent of 60+ vaccinated')      
    ax.vlines(pylab.date2num([datetime.datetime(2021, 3, 1, 0, 0)]),min(percent_elderly_vaccinated)-0.5,max(percent_elderly_vaccinated)+0.5,label='Elderly vaccinations begin',color='green',linestyles='dashed',linewidth=4)
    ax.legend(fontsize=8);pylab.title("Percent of 60+ vaccinated in KA ")
    fname=TMPDIR+'Karnataka_elderly_vaccinations.jpg'
    pylab.savefig(fname);pylab.close();print('saved fig to %s' %(fname))
    
    
    sp,ax=pylab.subplots()
    locator = mdates.AutoDateLocator(minticks=3, maxticks=7);formatter = mdates.ConciseDateFormatter(locator)
    ax.xaxis.set_major_locator(locator);    ax.xaxis.set_major_formatter(formatter) 

    ax.set_xlabel('Date')
    ax.set_ylabel('Percent of 45+ vaccinated in KA  (7-day MA)')
    ax.plot_date(pylab.date2num(dates),percent_over45_vaccinated,label='Percent of 45+ vaccinated')      
    ax.vlines(pylab.date2num([datetime.datetime(2021, 3, 1, 0, 0)]),min(percent_elderly_vaccinated)-0.5,max(percent_elderly_vaccinated)+0.5,label='Elderly vaccinations begin',color='green',linestyles='dashed',linewidth=4)
    ax.legend(fontsize=8);pylab.title("Percent of 45+ vaccinated in KA ")
    fname=TMPDIR+'Karnataka_over45_vaccinations.jpg'
    pylab.savefig(fname);pylab.close();print('saved fig to %s' %(fname))
      
  return out2
def mumbai_parse_cases(analysis=False,plot=True):
  r=csv.reader(open('0data/MumbaiCOVID19CasesByAge_mod.csv'))
  info=[]
  for i in r: info.append(i)
  info=info[-87:-7]; #start analyzing at 27 Jan
  
  dates=[datetime.datetime.strptime(i[0].replace('/21','/2021'),'%d/%m/%Y') for i in info]
  # ~ below60cases=np.int_(i[2:][:-4])
  below60cases=[]
  for i in info:
    try: below60cases.append( sum(np.int_(i[2:-4])) )
    except: print('failed for '+str(i))
  # ~ over60cases=np.int_(i[2:][-4:])
  over60cases=[sum(np.int_(i[-4:])) for i in info]
  
  dates=dates[1:]
  below60cases=np.diff(below60cases);over60cases=np.diff(over60cases)
  
  over60frac=100*(np.float_(over60cases)/(over60cases+below60cases))
  over60frac=moving_average(over60frac)
    
  if plot:
    sp,ax=pylab.subplots()
    dt,pt=tamil_nadu_parse_cases(analysis=True,plot=False)
    locator = mdates.AutoDateLocator(minticks=3, maxticks=7);formatter = mdates.ConciseDateFormatter(locator)
    ax.xaxis.set_major_locator(locator);    ax.xaxis.set_major_formatter(formatter) 

    ax.set_xlabel('Date')
    ax.set_ylabel('Percent of 60+ in daily cases (7-day MA)')
    ax.plot_date(dates,over60frac,label='Mumbai')
    ax.plot_date(dt,pt,label='Tamil Nadu')
    
    ax.vlines(pylab.date2num([datetime.datetime(2021, 3, 1, 0, 0)]),min(over60frac)-0.5,max(over60frac)+0.5,label='Elderly vaccinations begin',color='green',linestyles='dashed',linewidth=4)
    ax.legend(fontsize=8);pylab.title("Percentage of 60+ in Mumbai and Tamil Nadu's daily cases")
    fname=TMPDIR+'Mumbai_Tamil_nadu_elderly_cases_fraction.jpg'
    pylab.savefig(fname);pylab.close();print('saved fig to %s' %(fname))
    
  return (dates,below60cases,over60cases,over60frac)
  # ~ for i in info:
    # ~ date=datetime.datetime.strptime(i[0].replace('/21','/2021'),'%d/%m/%Y')
    # ~ below60cases=sum(np.int_(i[2:][:-4]))
    # ~ over60cases=np.int_(i[2:][-4:])
  
def tamil_nadu_parse_cases(analysis=False,plot=True,find_cis=False):
  r=csv.reader(open('csv_dumps/TN_cases.csv'))
  info=[]
  for i in r: info.append(i)
  info=info[1:]
  out=[]
  for i in info:
    date,a60=i
    date=datetime.datetime.strptime(date+'/2021','%d/%m/%Y')
    out.append((date,int(a60)))
    
  if analysis:
    print('analysing!')
    x=get_cases('Tamil Nadu',case_type='confirmed',return_full_series=True)
    #align
    lastdate=out[-1][0]
    x=[i for i in x if i[0]<=lastdate]
    datesc,c=zip(*x)
    dates,a60=zip(*out)
    
    a60=np.diff(a60)#[-1*len(dates):]
    c=np.diff(c)[-1*len(a60):]#[-1*len(dates):]
    
    # ~ frac=100*(np.array(moving_average(a60))/np.array(moving_average(c)))
    # ~ frac=100*np.array(moving_average(a60/c,window_size=7))    
    frac=100*np.array(a60/c)
    
    
        
    if find_cis:
      import statsmodels.api as sm;cis=[];ci0=[];ci1=[]
      for idx in range(len(c)):        
        cis.append(100*np.array(sm.stats.proportion_confint(a60[idx],c[idx])))
        ci0.append(100*np.array(sm.stats.proportion_confint(a60[idx],c[idx]))[0])
        ci1.append(100*np.array(sm.stats.proportion_confint(a60[idx],c[idx]))[1])
    
    # ~ dates=[i for i in dates if i>= datetime.datetime(2021, 2, 1, 0, 0)]
    dates=dates[7:]
    frac=frac[-1*len(dates):]    
    
    frac=[i[1] for i in zip(dates,frac) if i[0]!=datetime.datetime(2021, 3, 15, 0, 0)] #remove outlier on march 15
    frac=moving_average(frac)
    dates=[i for i in dates if i!=datetime.datetime(2021, 3, 15, 0, 0)]
    if plot:
      sp,ax=pylab.subplots()
      locator = mdates.AutoDateLocator(minticks=3, maxticks=7);formatter = mdates.ConciseDateFormatter(locator)
      ax.xaxis.set_major_locator(locator);    ax.xaxis.set_major_formatter(formatter) 

      ax.set_xlabel('Date')
      ax.set_ylabel('Percent of 60+ in daily cases (7-day MA)')
      ax.plot_date(pylab.date2num(dates),frac,label='Percent of 60+ in daily cases')      
      ax.vlines(pylab.date2num([datetime.datetime(2021, 3, 1, 0, 0)]),min(frac)-0.5,max(frac)+0.5,label='Elderly vaccinations begin',color='green',linestyles='dashed',linewidth=4)
      if find_cis:
        ax.fill_between(pylab.date2num(dates), ci0[:-6], ci1[:-6], color='grey', alpha=.25,label='95% CI') 
      ax.legend(fontsize=8);pylab.title("Percentage of 60+ in Tamil Nadu's daily cases")
      fname=TMPDIR+'Tamil_nadu_elderly_cases_fraction.jpg'
      pylab.savefig(fname);pylab.close();print('saved fig to %s' %(fname))
    if find_cis:
      return (dates,frac,cis)
    else:
      return (dates,frac)
    
    
    
  return out
def tamil_nadu_parse_csv():
  r=csv.reader(open('csv_dumps/TN_fatalities_Jul1_May10_2021.csv'))
  info=[]
  for i in r: info.append(i)
  info=info[1:]
  y=[]
  for i in info:
    pn,district,age,gender,origin,dodetect,doa,dod,dor=i[:9]
    comorb=' /'.join(i[9:])
    doa=datetime.datetime.strptime(doa,'%Y-%m-%d')
    dod=datetime.datetime.strptime(dod,'%Y-%m-%d')
    dor=datetime.datetime.strptime(dor,'%Y-%m-%d')
    f=generic_fatality(district,pn,age,gender,origin,comorb,doa,dod,dor,state='Tamil Nadu')
    y.append(f)
  return y
def kerala_parse_csv():
  r=csv.reader(open('csv_dumps/Kerala_fatalities_upto_mar13_2021.csv'))  
  info=[]
  for i in r: info.append(i)
  info=info[1:]
  y=[]
  for i in info:
    pn,district,age,gender,origin,dodetect,doa,dod,dor=i[:9]
    comorb=' /'.join(i[9:])
    # ~ doa=datetime.datetime.strptime(doa,'%Y-%m-%d')
    dod=datetime.datetime.strptime(dod,'%Y-%m-%d')
    if dor: dor=datetime.datetime.strptime(dor,'%Y-%m-%d')
    
    f=generic_fatality(district,pn,age,gender,origin,comorb,doa,dod,dor,state='Kerala')
    y.append(f)
  return y
 
  
def get_pfr(state='Tamil Nadu',start='',end='',date_type='',gender='',pfr_band=False,do_moving_average=False,ma_size=2,plot=False):
  if len(state)==2 and state in state_code_to_name: x=state;state=state_code_to_name[state];
  if state=='Tamil Nadu':    deaths=tamil_nadu_parse_csv()
  elif state=='Kerala':    deaths=kerala_parse_csv()
  elif state=='Karnataka':    deaths=karnataka_parse_csv(old=True);
  dd={}
  if start:
    deaths=[i for i in deaths if i.date_of_death>=start]
    if date_type=='admission':
      deaths=[i for i in deaths if i.date_of_admission>=start]
  if end:
    deaths=[i for i in deaths if i.date_of_death<=end]
    if date_type=='admission':
      deaths=[i for i in deaths if i.date_of_admission<=end]
  if gender:
    if gender in ['M','male','Male']: 
      deaths=[i for i in deaths if i.gender in ['M']]
    else:
      deaths=[i for i in deaths if i.gender in ['F']]
  allages=[i.age for i in deaths]
  for i in deaths:
    age=i.age
    if age in dd: dd[age]+=1
    else: dd[age]=1
  
  agedict=''
  if gender:
    if gender in ['M','male','Male']:      agedict=parse_census(state,'agedictm')
    else: agedict=parse_census(state,'agedictf')    
  else:    agedict=parse_census(state,'agedict')
  
  pfr={}
  
  for i in dd: 
    if i in agedict:   
      pfr[i]=100*(float(dd[i])/agedict[i])
      if do_moving_average:
        deaths_ma=sum([dd[j] for j in dd if j<=(i+ma_size) and j>=(i-ma_size)])
        ages_ma=sum([agedict[j] for j in agedict if j<=(i+ma_size) and j>=(i-ma_size)])
        pfr[i]=100*(float(deaths_ma)/ages_ma)
        # ~ histdata.append((i,deaths_ma))
  pfr_in_band=0;pfr_ratio={}
  if pfr_band:
    band=[60,65]
    dx=sum([dd[j] for j in dd if j<=band[1] and j>=band[0]])
    people_in_age_band=sum([agedict[j] for j in agedict if j<=band[1] and j>=band[0]])
    pfr_in_band=100*(float(dx)/people_in_age_band)
    
      
    
    # ~ print('got '+str(pfr_in_band))
  if plot:
    ages,pfrs=zip(*list(pfr.items()))
    label='PFR for '+state
    if start: label+=' from '+start.strftime('%d_%m_%Y')
    if end: label+=' to '+end.strftime('%d_%m_%Y')
    
    pylab.plot(ages,pfrs,'.',label=label)
    pylab.xlabel('age');pylab.ylabel('PFR');pylab.legend();pylab.title(label)
    pylab.savefig(TMPDIR+'/'+label+'.jpg');pylab.close()
    pylab.semilogy(ages,pfrs,'.',label=label+' semilog')
    pylab.xlabel('age');pylab.ylabel('PFR');pylab.legend();pylab.title(label+' semilogy')
    pylab.savefig(TMPDIR+'/'+label+'semilog.jpg');pylab.close()
  pfr=list(pfr.items());pfr.sort()
  if pfr_band:
    return pfr,pfr_in_band
  else:
    return pfr,allages
  
def tamil_nadu_bulletin_parser(bulletin='',return_page_range=False,clip_bulletin=False,return_date=False,dump_clippings=False):
  cmd='pdftotext  -layout "'+bulletin+'" tmp.txt';os.system(cmd)
  # ~ b=[i for i in open('tmp.txt').readlines() if i]
  b=[i for i in open('tmp.txt',encoding='utf-8',errors='ignore').readlines() if i]
  idx=0;page_count=1;page_range=[];got_start=False
  bulletin_date=''
  bd=[i for i in b if 'media bulletin' in i.lower()]
  bulletin_date_string='';bulletin_date=''
  if bd:
    bulletin_date=bd[0].split('lletin')[1].strip().replace('-','.').replace('/','.')
    bulletin_date_string=bulletin_date
    bulletin_date=datetime.datetime.strptime(bulletin_date,'%d.%m.%Y')
  if return_date: return bulletin_date
    
  for i in b:
    if '\x0c' in i: page_count+=1    
    if 'Death in'.lower() in i.lower() and not got_start:
      page_range.append(page_count)
      got_start=True
    if 'Passengers entered Tamil Nadu'.lower() in i.lower():
      page_range.append(page_count-1)
    idx+=1
  if return_page_range: return page_range

  if clip_bulletin:
    print(("clipping buletin "+bulletin+"to  page range "+str(page_range)))
    cmd='pdfseparate -f '+str(page_range[0])+' -l '+str(page_range[1])+' "'+bulletin+'" tmp-%04d.pdf';os.system(cmd)
    cmd='pdfunite tmp-*pdf joined.pdf';os.system(cmd)
    cmd='mv -fv joined.pdf "'+bulletin+'"';os.system(cmd)

  cmd='pdftotext -nopgbrk  -layout "'+bulletin+'" tmp.txt';os.system(cmd)

  #find clipping of death info
  # ~ b=[i.strip() for i in open('tmp.txt').readlines() if i.strip()]
  b=[i.strip() for i in open('tmp.txt',encoding='utf-8',errors='ignore').readlines() if i.strip()]
  idx=0;indices=[];b_idx=0
  for i in b:    
    if 'Death Case No' in i:
      idx+=1;indices.append(b_idx)    
    b_idx+=1
  #last elem, assume 10 more lines
  if indices:
    indices.append(indices[-1]+10)
  else:
    print(('ERROR! Could not find clip indices in: '+bulletin))

  deaths=[]

  if dump_clippings:
    a=open('parsed_clippings.txt','a')
    a.write('##BULLETIN_DATE '+bulletin_date_string+'\n')
    for j in range(len(indices)-1):
      clip=b[indices[j]:indices[j+1]]
      for cl in clip: a.write(cl+'\n')
    a.close()
    # ~ print 'dumped clippings'
    return
    
def tamil_nadu_parse_clippings():
  b=[i.strip() for i in open('parsed_clippings.txt').readlines() if i.strip()]
  idx=0;indices=[];b_idx=0;bulletin_date_string=''
  
  for i in b:    
    if 'Death Case No' in i:
      if '##BULLETIN_DATE' in b[b_idx-1]:
        bulletin_date_string=b[b_idx-1].split('##BULLETIN_DATE')[1].strip()
        # ~ print 'found date: '+bulletin_date_string+' at b_idx '+str(b_idx)
    
      idx+=1;indices.append((b_idx,bulletin_date_string))      
    b_idx+=1
  #last elem, assume 10 more lines
  if indices:
    indices.append((indices[-1][0]+10,indices[-1][1]))
  else:
    print(('ERROR! Could not find clip indices in: '+bulletin))

  deaths=[]

  bulletin_date_string=''
  for j in range(len(indices)-1):
    bulletin_date_string=indices[j][1]
    try:
      bulletin_date=datetime.datetime.strptime(bulletin_date_string,'%d.%m.%Y')
    except:
      print('error in getting bulletin_date with bulletin_date_string: %s' %(bulletin_date_string))
      if not bulletin_date_string: print(indices);print(j)
      return indices

    start=indices[j][0];end=indices[j+1][0]
    
    clip=b[start:end]
    death_case_no=clip[0].strip().split('Death Case No')[1].replace(':','').strip().replace('.','')
    if 'no' in death_case_no.lower(): death_case_no=death_case_no.lower().replace('no','').strip()
    cons=' '.join(clip[1:])
    
    if 'included in the list' in cons.lower(): 
      # ~ print('included in list.skipping');
      continue

    
    try:
      age=cons.split()[1]      
    except:
      print(('error splirtting cons: '+cons+' '+str(indices[j])))
    if age.lower()=='years': age=cons.split()[0].replace('A','')

    
    if not age.isdigit():
      try: assert(age[0])
      except:
        print(('error splirtting cons: '+cons+' '+str(indices[j])))
      if age[0].isdigit(): #starts right but has alpha
        # ~ print 'incorrect age at index: '+str(j)+' with cons: '+cons
        # ~ return
        x0=age[0]
        for j in range(1,len(age)):
          if age[j].isdigit(): x0+=age[j]
        age=x0
      else:
        if 'year' in cons and 'years' not in cons:
          print(('incorrect age at index: '+str(j)+' with cons: '+cons))
          return
        age=cons.lower().split('year')[0].split()[-1]
        if not age.isdigit():
          print(age)
          print(('could find find age for '+cons))
          return
    # ~ death_case_no=int(death_case_no);age=int(age)
    gender=''
    if 'old' in cons:
      try:
        gender=cons.split('old')[1].split()[0].strip()
      except:
        print(('error splitingg gender, cons: '+cons))
        return
        
    else:
      if 'years' in cons.lower():
        gender=cons.lower().split('years')[1].split()[0].strip()
      elif 'year' in cons.lower():
        gender=cons.lower().split('year')[1].split()[0].strip()
      else:
        print(('no "old" or "years" for gender in  cons: '+cons))
        return
    gender=gender.replace(',','')
    
    
    if 'female' in gender.lower(): gender='F'
    elif 'male' in gender.lower(): gender='M'
    
    district=''
    try:
      district=cons.lower().split('from')[1].split()[0].strip().lower().replace(',','')
    except:
      print(('\nerror in getting district for cons: '+cons))
      return
      
    
    cons=cons.replace('admiitted on','admitted on'); #fix typo
    doa_eq_dod=False
    date_of_admission=''
    if 'admitted' in cons:
      if 'admitted with' in cons and 'admitted on' not in cons:
        try:
          date_of_admission=cons.split('admitted')[1].split(' on ')[1].strip().split()[0].strip()
        except:
          print(('error getting doa with cons: '+cons))
          return
      elif 'admitted on' not in cons:
        date_of_admission=cons.split('admitted')[1].split()[0].strip()
        if date_of_admission.strip()=='in': date_of_admission=''
    if 'admitted on' in cons:
      date_of_admission=cons.split('admitted on')[1].split()[0].strip()
    elif 'brought dead' in cons.lower(): doa_eq_dod=True
    else:
      if not date_of_admission:
        # ~ print '\nerror in doa, cions: '+cons
        pass

    date_of_death=''
    if 'died on' in cons.lower():
      date_of_death=cons.lower().split('died on')[1].split()[0].strip()
    elif 'died' in cons.lower():
      date_of_death=cons.lower().split('died')[1].split()[1].strip()
    elif 'dead on' in cons.lower():
      date_of_death=cons.lower().split('dead on ')[1].strip().split()[0].strip()
      # ~ print date_of_death;print cons
    else:
      print(('error finding dod from cons: '+cons))
    if doa_eq_dod: date_of_admission=date_of_death
    date_of_death=date_of_death.replace('/','.')
    # ~ cause_of_death=cons.split('due to')[1].strip().split('.')[0]

    date_of_admission=date_of_admission.replace('-','.').replace('2020in','2020').replace(',','')
    #fix typos
    if date_of_admission.endswith('.20'): date_of_admission+='20'
    elif date_of_admission.endswith('.200'): date_of_admission=date_of_admission[:-1]+'20'
    
    date_of_death=date_of_death.replace('-','.').replace('2020in','2020').replace(',','')
    if date_of_death.endswith('.20'): date_of_death+='20'
    try:
      date_of_admission=date_of_admission.replace('/','.').replace('-','.')
      if date_of_admission: doa=datetime.datetime.strptime(date_of_admission,'%d.%m.%Y')
    except:
      print(('error creating datetimes with doa: '+date_of_admission+' with date_of_death: '+date_of_death+'\ncons: '+cons))
      return
    try:
      date_of_death=date_of_death.replace('/','.').replace('-','.')
      dod=datetime.datetime.strptime(date_of_death,'%d.%m.%Y')
    except:
      print(('error getting dod with date_of_death: '+date_of_death+'\ncons: '+cons))

    
    comorbidities=''
    if ', with ' in cons: comorbidities=cons.split(', with')[1].split('admitted')[0].strip()
    cons2=cons.replace('with complaints of ',' complaints of')
    if ' with ' in cons2: comorbidities=cons2.split(' with')[1].split('admitted')[0].strip()
    
    info='%s : %s yrs: Sex: %s, District: %s\nDOA: %s, DOD: %s' %(death_case_no,age,gender,district,date_of_admission,date_of_death)
    if comorbidities:info+='\nComorbidiies: %s' %(comorbidities)
    # ~ a.write(info+'\n\n')

    # ~ comorbidities=[i.strip() for i in comorbidities.split('/')]
    
    f=generic_fatality(district,death_case_no,age,gender,'',comorbidities,doa,dod,bulletin_date,state='Tamil Nadu')
    deaths.append(f)
  # ~ a.close()
    
  
  print((len(indices)-1,' death cases found'))
  return deaths
  
def karnataka_bulletin_get_margins_confirmed(bulletin='06_18_2020.pdf',page_range=(5,12),execute=True,debug_clip='',debug=False):
  cmd='pdftotext -x 0 -y 0 -W 1000 -H 2000 -bbox-layout -nopgbrk -layout -f '+str(page_range[0])+' -l '+str(page_range[1])+' "'+bulletin+'" tmp.txt';os.system(cmd)
  from bs4 import BeautifulSoup
  soup=BeautifulSoup(open('tmp.txt').read(),'lxml')
  d_idx=[i for i in range(len(soup('block'))) if soup('block')[i]('word')[0].text.strip().lower()=='district']  
  if not d_idx:
    print(('could not find "block" for District in '+bulletin+' with range '+str(page_range)))
    return
  d=soup('block')[d_idx[0]]
  
  #find x,y of block
  xmin=float(d.get('xmin'));  xmax=float(d.get('xmax'))
  ymin=float(d.get('ymin'));  ymax=float(d.get('ymax'))

  #get all blocks between y=0 and y=2*ymax
  hblocks=[i for i in soup('block') if float(i.get('ymin'))>0 and float(i.get('ymax'))<(2*ymax)]
  hwords=[i for i in soup('word') if float(i.get('ymin'))>0 and float(i.get('ymax'))<(2*ymax)]
  # ~ return soup,hblocks,hwords

  bboxes={}
  
  #history
  history=[i for i in hblocks if i.text.strip().startswith('History')]
  if not history: history=[i for i in hwords if i.text.startswith('History')]
  if not history: history=[i for i in hblocks if i.text.startswith('Description')]
  if not history: history=[i for i in hwords if i.text.startswith('Description')]
  if not history:
    print('could not find block for history')
    return
  else:
    history=history[0];d=history
    xmin=float(d.get('xmin'));  xmax=float(d.get('xmax'))
    bboxes['history']=(xmin,xmax)

  #isolated
  isolated=[i for i in hblocks if i.text.strip().startswith('Isolated')]
  if not isolated: isolated=[i for i in hwords if i.text.startswith('Isolated')]
  if not isolated:
    print('could not find block for isolated')
    return
  else:
    isolated=isolated[0];d=isolated
    xmin=float(d.get('xmin'));  xmax=float(d.get('xmax'))
    bboxes['isolated']=(xmin,xmax)

  xcut=0
  xcut=bboxes['history'][1] + (bboxes['isolated'][0]-bboxes['history'][1])*0.5  
  xcut=int(xcut)+1
  
  if debug_clip or execute:
    if not xcut:
      print(('could not find margins(confirmed) for bulletin: '+ str(bulletin)))
      return
    w=str(xcut)
    cmd='pdftotext -x 0  -W '+w+' -y 0 -H 1000  -nopgbrk -layout -f '+str(page_range[0])+' -l '+str(page_range[1])+' '+bulletin+' tmp.txt'
    if debug_clip: print(cmd)
    os.system(cmd)
    if debug_clip: print('created debug clip in tmp.txt ')
  return xcut
  
def karnataka_bulletin_get_margins(bulletin='09_09_2020.pdf',page_range=(19,23),debug_clip='',debug=False):
  cmd='pdftotext -x 0 -y 0 -W 1000 -H 2000 -bbox-layout -nopgbrk -layout -f '+str(page_range[0])+' -l '+str(page_range[1])+' "'+bulletin+'" tmp.txt';os.system(cmd)
  from bs4 import BeautifulSoup
  soup=BeautifulSoup(open('tmp.txt').read(),'html.parser')
  d_idx=[i for i in range(len(soup('block'))) if soup('block')[i]('word')[0].text.strip().lower()=='district']  
  if not d_idx:
    print(('could not find "block" for District in '+bulletin+' with range '+str(page_range)))
    return
  d=soup('block')[d_idx[0]]
  
  #find x,y of block
  xmin=float(d.get('xmin'));  xmax=float(d.get('xmax'))
  ymin=float(d.get('ymin'));  ymax=float(d.get('ymax'))

  #get all blocks between y=0 and y=2*ymax
  hblocks=[i for i in soup('block') if float(i.get('ymin'))>0 and float(i.get('ymax'))<(2*ymax)]
  hwords=[i for i in soup('word') if float(i.get('ymin'))>0 and float(i.get('ymax'))<(2*ymax)]

  bboxes={}
  #s.no
  sno=[i for i in hblocks if i.text.strip().startswith('Sl.')]
  if not sno:
    print('could not find block for serial number')
    return
  else:
    sno=sno[0];d=sno
    xmin=float(d.get('xmin'));  xmax=float(d.get('xmax'))
    bboxes['sno']=(xmin,xmax)

  #district
  district=[i for i in hblocks if i.text.strip().startswith('District')]
  if not district:
    print('could not find block for district')
    return
  else:
    district=district[0];d=district
    xmin=float(d.get('xmin'));  xmax=float(d.get('xmax'))
    bboxes['district']=(xmin,xmax)
  
  #State P No
  spno=[i for i in hblocks if i.text.strip().startswith('State')]
  if not spno:
    print('could not find block for State P. no')
    return
  else:
    spno=spno[0];d=spno
    xmin=float(d.get('xmin'));  xmax=float(d.get('xmax'))
    bboxes['spno']=(xmin,xmax)

  #age
  age=[i for i in hblocks if i.text.strip().startswith(('Age','Ag'))]
  # ~ age=[i for i in hblocks if i.text.strip().startswith(('Age')]
  if not age:
    print('could not find block for Age')
    return
  else:
    age=age[0];d=age
    xmin=float(d.get('xmin'));  xmax=float(d.get('xmax'))
    bboxes['age']=(xmin,xmax)

  #sex
  sex=[i for i in hblocks if i.text.strip().startswith('Sex')]
  if not sex: sex=[i for i in hwords if i.text.strip().startswith('Sex')]
  if not sex:    
    print('could not find block for sex')
    return
  else:
    sex=sex[0];d=sex
    xmin=float(d.get('xmin'));  xmax=float(d.get('xmax'))
    bboxes['sex']=(xmin,xmax)

  #desc
  desc=[i for i in hblocks if i.text.strip().startswith('Desc')]
  if not desc: desc=[i for i in hwords if i.text.strip().startswith('Desc')]
  if not desc:
    print('could not find block for description')
    return
  else:
    desc=desc[0];d=desc
    xmin=float(d.get('xmin'));  xmax=float(d.get('xmax'))
    bboxes['desc']=(xmin,xmax)

  #symp
  symp=[i for i in hblocks if i.text.strip().startswith('Sympt')]
  if not symp: symp=[i for i in hwords if i.text.strip().startswith('Sympt')]
  if not symp:
    print('could not find block for symptoms')
    return
  else:
    symp=symp[0];d=symp
    xmin=float(d.get('xmin'));  xmax=float(d.get('xmax'))
    bboxes['symp']=(xmin,xmax)

  #comorb
  comorb=[i for i in hblocks if i.text.strip().startswith('Co-')]
  if not comorb: comorb=[i for i in hwords if i.text.strip().startswith('Co-')]
  if not comorb:
    print('could not find block for comorb')
    return
  else:
    comorb=comorb[0];d=comorb
    xmin=float(d.get('xmin'));  xmax=float(d.get('xmax'))
    bboxes['comorb']=(xmin,xmax)

  #doa
  doa=[i for i in hblocks if i.text.strip().startswith('DOA')]
  if not doa: doa=[i for i in hwords if i.text.strip().startswith('DOA')]
  if not doa:
    print('could not find block for DOA')
    return
  else:
    doa=doa[0];d=doa
    xmin=float(d.get('xmin'));  xmax=float(d.get('xmax'))
    bboxes['doa']=(xmin,xmax)

  #dod
  dod=[i for i in hblocks if i.text.strip().startswith('DOD')]
  if not dod:  dod=[i for i in hwords if i.text.strip().startswith('DOD')]
  if not dod:
    print('could not find block for DOD')
    return
  else:
    dod=dod[0];d=dod
    xmin=float(d.get('xmin'));  xmax=float(d.get('xmax'))
    bboxes['dod']=(xmin,xmax)

  #place
  place=[i for i in hblocks if i.text.strip().startswith('Place')]
  if not place: place=[i for i in hwords if i.text.strip().startswith('Place')]
  if not place:
    if debug: print('could not find block for place of deaths')
    
  else:
    place=place[0];d=place
    xmin=float(d.get('xmin'));  xmax=float(d.get('xmax'))
    bboxes['place']=(xmin,xmax)

  margins={};#xmin,width

  hack=False; #needed in some cases with comorb
  #sno
  diff=(bboxes['district'][0]-bboxes['sno'][1])/2.;#halfway
  xmin=bboxes['sno'][0]/2.;
  xmax=bboxes['sno'][1]+diff
  margins['sno']=(int(xmin),int(xmax-xmin))
  #district  
  xmin=bboxes['district'][0]-diff;
  diff=(bboxes['spno'][0]-bboxes['district'][1])/2.;#halfway
  xmax=bboxes['district'][1]+diff
  margins['district']=(int(xmin),int(xmax-xmin))
  #spno  
  xmin=bboxes['spno'][0]-(diff*0.33);#biased towards spno, since sometime district column "intrudes"
  diff=(bboxes['age'][0]-bboxes['spno'][1])/2.;
  xmax=bboxes['spno'][1]+diff
  margins['spno']=(int(xmin),int(xmax-xmin))
  #age  
  xmin=bboxes['age'][0]-diff;
  diff=(bboxes['sex'][0]-bboxes['age'][1])/2.;#halfway
  xmax=bboxes['age'][1]+diff
  margins['age']=(int(xmin),int(xmax-xmin))
  #sex  
  xmin=bboxes['sex'][0]-diff;
  diff=(bboxes['desc'][0]-bboxes['sex'][1])/2.;#halfway
  xmax=bboxes['sex'][1]+diff
  margins['sex']=(int(xmin),int(xmax-xmin))
  #desc
  xmin=bboxes['desc'][0]-diff;
  diff=(bboxes['symp'][0]-bboxes['desc'][1])*0.33;##biased towards desc, since sometimes symp column "intrudes"
  xmax=bboxes['desc'][1]+diff
  margins['desc']=(int(xmin),int(xmax-xmin))
  #symp
  xmin=bboxes['symp'][0]-diff;
  diff=(bboxes['comorb'][0]-bboxes['symp'][1])/2;#halfway
  try:
    assert(diff>0)
  except AssertionError:
    print(('bbox of symp '+str(bboxes['symp'])+' and comorb: '+str(bboxes['comorb'])))
    diff=0
    hack=True
  xmax=bboxes['symp'][1]+diff
  margins['symp']=(int(xmin),int(xmax-xmin))
  #comorb
  xmin=bboxes['comorb'][0]-(diff*0.67);#biased towards comorb, since sometimes symp column "intrudes"
  if hack: xmin=bboxes['symp'][1]+5
  diff=(bboxes['doa'][0]-bboxes['comorb'][1])*0.33;#biased towards comorb, since sometimes doa column "intrudes"
  xmax=bboxes['comorb'][1]+diff
  margins['comorb']=(int(xmin),int(xmax-xmin))
  #doa
  xmin=bboxes['doa'][0]-(diff*1.33);
  diff=(bboxes['dod'][0]-bboxes['doa'][1])/2.;#halfway
  xmax=bboxes['doa'][1]+diff
  margins['doa']=(int(xmin),int(xmax-xmin))
  #place maay or may not be there
  if 'place' in bboxes:
    #dod
    xmin=bboxes['dod'][0]-diff;
    diff=(bboxes['place'][0]-bboxes['dod'][1])/2.;#halfway
    xmax=bboxes['dod'][1]+diff
    margins['dod']=(int(xmin),int(xmax-xmin))
    #place
    xmin=bboxes['place'][0]-diff;
    diff=20;#fixed
    xmax=bboxes['place'][1]+diff
    margins['place']=(int(xmin),int(xmax-xmin))
  else:
    xmin=bboxes['dod'][0]-diff;
    # ~ diff=(bboxes['place'][0]-bboxes['dod'][1])/2.;#halfway
    diff=20; #fixed value
    xmax=bboxes['dod'][1]+diff
    margins['dod']=(int(xmin),int(xmax-xmin))
  margins['doadod']=(margins['doa'][0],margins['doa'][1]+margins['dod'][1])
  margins['snodistrict']=(margins['sno'][0],margins['sno'][1]+margins['district'][1])
  margins['spnotodesc']=(margins['spno'][0],margins['spno'][1]+margins['age'][1]+margins['sex'][1]+margins['desc'][1])
  
  if debug_clip:
    if (debug_clip not in margins) :
      print(('%s was not a valid entry' %(debug_clip)))
      return
    x=str(margins[debug_clip][0])
    w=str(margins[debug_clip][1])
    cmd='pdftotext -x '+x+'  -W '+w+' -y 0 -H 1000  -nopgbrk -layout -f '+str(page_range[0])+' -l '+str(page_range[1])+' '+bulletin+' tmp.txt'
    print(cmd)
    os.system(cmd)
    print(('created debug clip in tmp.txt of '+debug_clip))
  return margins

def helper_map_district_start_char_to_fullname(startchars=''):
  for k in karnataka_districts_map:
    if startchars.lower().startswith(k):
      return karnataka_districts_map[k]
def helper_correlate_signals(x,y,plot=False):
  if len(x)!=len(y):
    print(('array length %d %d are not same' %(len(x),len(y))))
  # ~ corr=numpy.correlate(x-numpy.mean(x),y-numpy.mean(y),mode='full')
  corr=numpy.correlate(x,y,mode='full')
  lag = corr.argmax()-(len(x)- 1)
  if plot:
    # ~ import pylab
    pylab.plot(corr)
  print(('best lag between signals: '+str(lag)))
  return corr
  
def helper_plot_linear_fit(x,y,label='',color='',xtype='date',extrapolate=''):
  # ~ import pylab
  if extrapolate: extrapolate=int(extrapolate)
#  xr=numpy.arange(len(x))
#  coef=numpy.polyfit(xr,y,1)
  coef=numpy.polyfit(x,y,1)
  poly1d_fn=numpy.poly1d(coef)
  # ~ pylab.plot(x,y, 'yo', x, poly1d_fn(x), '--k',label='Best linear fit')
  # ~ pylab.plot_date(x,poly1d_fn(xr), 'g',label='Best linear fit')
  if not color:    color='g'
  if not label:    label='Best linear fit'
  
  if extrapolate: 
#      xr=np.arange(len(x)+int(extrapolate))
      if xtype:
          x2=[pylab.date2num(pylab.num2date(x[-1])+datetime.timedelta(days=i)) for i in range(1,extrapolate+1)]
          x=np.append(x,x2)


  if xtype:
    pylab.plot_date(x,poly1d_fn(x),color,label=label)
  else:
    pylab.plot(x,poly1d_fn(x),color,label=label)

def helper_plot_exponential_fit(x,y,label='',color=''):
  # ~ import pylab  
  coef=numpy.polyfit(x,numpy.log(y),1)
  poly1d_fn=numpy.poly1d(coef)
  # ~ pylab.plot(x,y, 'yo', x, poly1d_fn(x), '--k',label='Best linear fit')
  # ~ pylab.plot_date(x,poly1d_fn(xr), 'g',label='Best linear fit')
  if not color:    color='r'
  if not label:    label='Best Exponential fit'
  
  pylab.plot(x,numpy.exp(poly1d_fn(x)),color,label=label)
  
def helper_plot_loglog_fit(x,y,label='',color=''):
  # ~ import pylab  
  coef=numpy.polyfit(numpy.log(x),numpy.log(y),1)
  poly1d_fn=numpy.poly1d(coef)
  # ~ pylab.plot(x,y, 'yo', x, poly1d_fn(x), '--k',label='Best linear fit')
  # ~ pylab.plot_date(x,poly1d_fn(xr), 'g',label='Best linear fit')
  if not color:    color='r'
  if not label:    label='Best Log-Log fit'
  
  pylab.plot(x,numpy.exp(poly1d_fn(np.log(x))),color,label=label)
  
  
def helper_get_mean_timeseries(recoveries):
  d1=datetime.date(2020,7,14);d2=datetime.date(2021,2,11);delta=d2-d1
  datetimes=[(d1 + datetime.timedelta(days=i)) for i in range(delta.days + 1)]
  datetimes=[datetime.datetime.combine(i,datetime.time(0, 0)) for i in datetimes]
  # ~ return datetimes
  # ~ dates=[(d1 + datetime.timedelta(days=i)).strftime('%Y-%m-%d') for i in range(delta.days + 1)]
  mean_values=[]
  for dd in datetimes:
    r=[i.detection_discharge_interval for i in recoveries if i.date_of_discharge==dd]
    r1=[i.detection_discharge_interval for i in recoveries if i.date_of_discharge==dd and i.district.startswith('Bengaluru')]
    r2=[i.detection_discharge_interval for i in recoveries if i.date_of_discharge==dd and not i.district.startswith('Bengaluru')]
    if not r:
      print(('no recovery info for '+str(dd)))
      continue
    m1=0;m2=0
    if r1: m1=numpy.mean(r1)
    if r2: m2=numpy.mean(r2)
    # ~ mean_values.append((dd,numpy.mean(r),numpy.mean(r1),numpy.mean(r2)))
    mean_values.append((dd,numpy.mean(r),m1,m2))
    # ~ mean_values.append((dd,numpy.median(r),numpy.median(r1),numpy.median(r2)))
  return mean_values

class mumbaihosp():
  date=''
  icu_cap=0;icu_used=0;
  vent_cap=0;vent_used=0;
  oxy_cap=0;oxy_used=0;
  
  def __init__(self,row):
    try:
      self.date,self.icu_cap,self.icu_used,x0,self.oxy_cap,self.oxy_used,x1,self.vent_cap,self.vent_used,x2=row    
    except:
      print(('error parsing '+str(row)))
    self.date=datetime.datetime.strptime(self.date,'%Y-%m-%d')
    self.icu_cap=int(self.icu_cap)
    self.oxy_cap=int(self.oxy_cap)
    self.vent_cap=int(self.vent_cap)
    self.icu_used=int(self.icu_used)
    self.oxy_used=int(self.oxy_used)
    self.vent_used=int(self.vent_used)
  def info(self):
    info='Date: %s\n' %(self.date.strftime('%d-%m'))
    info+='\tICU  : %d/%d used\n' %(self.icu_used,self.icu_cap)
    info+='\tVent.: %d/%d used\n' %(self.vent_used,self.vent_cap)
    info+='\tOxyg.: %d/%d used\n' %(self.oxy_used,self.oxy_cap)
    print(info)

def get_mobility(state='Uttar Pradesh',district='',do_moving_average=True,plot=False,plot_days='',special_sum=False):
    if len(state)==2 and state in state_code_to_name: x=state;state=state_code_to_name[state];
    import csv;info=[]
    r=csv.reader(open('2020_IN_Region_Mobility_Report.csv'))
    
    for i in r: info.append(i);
    x=[i for i in info if i[2]==state and i[3]==district]
    y=[]
    for i in x:
      dt=datetime.datetime.strptime(i[8],'%Y-%m-%d')
      recr=int(i[9])
      groc_phar=int(i[10])
      parks=int(i[11])
      trans=int(i[12])
      wrksp=int(i[13])
      resi=int(i[14])
      avg=(recr+groc_phar+parks+trans+wrksp+resi)/6.
      if special_sum:        
        avg_minus_resi=(recr+groc_phar+parks+trans+wrksp)/5.
        y.append((dt,recr,groc_phar,parks,trans,wrksp,resi,avg_minus_resi))
      else:
        y.append((dt,recr,groc_phar,parks,trans,wrksp,resi,avg))
    
    r=csv.reader(open('2021_IN_Region_Mobility_Report.csv'));info=[]
    for i in r: info.append(i);
    x=[i for i in info if i[2]==state and i[3]==district]
    for i in x:
      dt=datetime.datetime.strptime(i[8],'%Y-%m-%d')
      recr=int(i[9])
      groc_phar=int(i[10])
      parks=int(i[11])
      trans=int(i[12])
      wrksp=int(i[13])
      resi=int(i[14])
      avg=(recr+groc_phar+parks+trans+wrksp+resi)/6.
      if special_sum:        
        avg_minus_resi=(recr+groc_phar+parks+trans+wrksp)/5.
        y.append((dt,recr,groc_phar,parks,trans,wrksp,resi,avg_minus_resi))
      else:
        y.append((dt,recr,groc_phar,parks,trans,wrksp,resi,avg))

    dates,recr,groc,parks,trans,wrksp,resi,avg=zip(*y)
#    print(len(resi),len(parks))
#    print(recr)

    if do_moving_average:
        recr=moving_average(recr)
        groc=moving_average(groc)
        parks=moving_average(parks)
        trans=moving_average(trans)
        wrksp=moving_average(wrksp)
        resi=moving_average(resi)
        avg=moving_average(avg)
    y=list(zip(dates,recr,groc,parks,trans,wrksp,resi,avg))

    if plot:
        if plot_days:
            pass
        # ~ if district: #compare with avg of district vs state
            # ~ dates2,x1,x2,x3,x4,x5,x6,state_avg=zip(*get_mobility(state=state,district=''))
            # ~ dates2=pylab.date2num(dates2);dates=pylab.date2num(dates)
            # ~ ax=pylab.axes()
            # ~ locator = mdates.AutoDateLocator(minticks=3, maxticks=7)
            # ~ formatter = mdates.ConciseDateFormatter(locator)
            # ~ ax.xaxis.set_major_locator(locator)
            # ~ ax.xaxis.set_major_formatter(formatter) 
            # ~ ax.plot_date(dates,avg,label=district+' avg. change from baseline')
            # ~ ax.plot_date(dates2,state_avg,label=state+' avg. change from baseline')
            # ~ ax.set_xlabel('dates');ax.set_ylabel('Percent Change in mobility from baseline in '+district+' vs whole '+state);
            # ~ ax.legend(fontsize=6)
            # ~ ax.set_title('Mobility trends in '+district+' vs '+state)

            # ~ pylab.savefig(TMPDIR+district+' vs '+state+' mobility trends.jpg');pylab.close()


        # ~ else:
            dates=pylab.date2num(dates)
            if plot_days:
              dates=dates[-1*plot_days:]
              recr=recr[-1*plot_days:]
              trans=trans[-1*plot_days:]
              wrksp=wrksp[-1*plot_days:]
              groc=groc[-1*plot_days:]
              resi=resi[-1*plot_days:]
              parks=parks[-1*plot_days:]
              avg=avg[-1*plot_days:]
            ax=pylab.axes()
            locator = mdates.AutoDateLocator(minticks=3, maxticks=7)
            # ~ formatter = mdates.ConciseDateFormatter(locator)
            formatter = mdates.ConciseDateFormatter(locator)
            ax.xaxis.set_major_locator(locator)
            ax.xaxis.set_major_formatter(formatter) 
            ax.plot_date(dates,recr,label='Retail')
            ax.plot_date(dates,groc,label='Grocery')
            ax.plot_date(dates,parks,label='Parks')
            ax.plot_date(dates,trans,label='Transport')
            ax.plot_date(dates,wrksp,label='Workplace')
            ax.plot_date(dates,resi,label='Residence')
            ax.plot_date(dates,avg,label='Average')
            ax.set_xlabel('dates');ax.set_ylabel('Percent Change in mobility from baseline');
            ax.legend(fontsize=6)
            loc=state
            if district: loc=district+' district of '+state
            if not loc: loc='India'
            ax.set_title('Mobility trends in '+loc)
  
            pylab.savefig(TMPDIR+loc+' mobility trends.jpg');pylab.close()
            #avg vs pos
            if (not district) and (loc!='India'):
                dates5,pos=zip(*get_positivity(state))
                if plot_days:
                    dates5=dates5[-1*plot_days:]
                    pos=pos[-1*plot_days:]
                plot2(dates,avg,pylab.date2num(dates5),pos,label1='Average change in mobility (7-day MA)',label2='TPR (7-day MA)',color2='green',state=state)


 
    return y

def parse_mumbai_beds():
  infile='csv_dumps/MumbaiBeds.csv'
  import csv;info=[]
  r=csv.reader(open(infile))
  for i in r: info.append(i);
  info=info[1:]
  # ~ objs=[mumbaihosp(i) for i in info[40:]]
  objs=[mumbaihosp(i) for i in info[19:]]
  # ~ return (info,objs)
  return objs

def mumbai_analysis():
  x=get_cases_district(state='Maharashtra',district='Mumbai',case_type='deaths_delta')
  x[49]=(datetime.datetime(2020, 6, 16, 0, 0), 69) #exclude sudden addition of 900+ deaths on June 16
  
  x=[i for i in x if i[0]>=datetime.datetime(2020,6,1,0,0)]
  dates,deaths=list(zip(*x))
  x=get_cases_district(state='Maharashtra',district='Mumbai',case_type='active')
  x=[i for i in x if i[0]>=datetime.datetime(2020,6,1,0,0)]
  dates2,actives=list(zip(*x))
  deaths=moving_average(deaths);actives=moving_average(actives)

  hos=parse_mumbai_beds()
  dates3=[i.date for i in hos];
  icu_used=[i.icu_used for i in hos];vent_used=[i.vent_used for i in hos];oxy_used=[i.oxy_used for i in hos]
  icu_cap=[i.icu_cap for i in hos];vent_cap=[i.vent_cap for i in hos];oxy_cap=[i.oxy_cap for i in hos]
  

  dates=pylab.date2num(dates);dates2=pylab.date2num(dates2);dates3=pylab.date2num(dates3)
  deaths=moving_average(deaths);actives=moving_average(actives)
  icu_used=moving_average(icu_used);vent_used=moving_average(vent_used);oxy_used=moving_average(oxy_used)
  icu_cap=moving_average(icu_cap);vent_cap=moving_average(vent_cap);oxy_cap=moving_average(oxy_cap)

  icu_pc=[100*float(i.icu_used)/i.icu_cap for i in hos];vent_pc=[100*float(i.vent_used)/i.vent_cap for i in hos];oxy_pc=[100*float(i.oxy_used)/i.oxy_cap for i in hos]

  # ~ pylab.plot_date(dates3,icu_cap,label='ICU beds')
  # ~ pylab.plot_date(dates3,vent_cap,label='Vent beds')
  # ~ pylab.plot_date(dates3,oxy_cap,label='Oxyg. beds')
  # ~ pylab.xlabel('Date')
  # ~ pylab.ylabel('Number of beds')
  # ~ title='Mumbai hospital capacity over time'
  # ~ pylab.title(title);pylab.legend()

  # ~ pylab.plot_date(dates3,icu_pc,label='ICU utilization(%)')
  # ~ pylab.plot_date(dates3,vent_pc,label='Vent utilization(%)')
  # ~ pylab.plot_date(dates3,oxy_pc,label='Oxyg. utilization(%)')
  # ~ pylab.xlabel('Date')
  # ~ pylab.ylabel('Mumbai hospital utilization percentage (7-day MA)')
  # ~ title='Mumbai hospital utilization'
  # ~ pylab.title(title);pylab.legend()
  
  # ~ sp,ax=pylab.subplots()
  # ~ color = 'tab:blue'
  # ~ ax.set_xlabel('Date')
  # ~ ax.set_ylabel('Mumbai ICU beds (7-day MA)',color=color)
  # ~ ax.plot_date(dates3,icu_used,color=color,label='ICU beds')
  # ~ ax.tick_params(axis='y', labelcolor=color)
  # ~ ax.legend(loc='lower left');
  # ~ ax2=ax.twinx()
  # ~ color = 'tab:red'
  # ~ ax2.set_ylabel('Mumbai Vent. beds (7-day MA)',color=color)
  # ~ ax2.plot_date(dates3,vent_used,color=color,label='Vent beds')
  # ~ ax2.tick_params(axis='y', labelcolor=color)
  # ~ ax2.legend(loc='lower right');
  # ~ sp.tight_layout()
  # ~ title='Mumbai ICU use vs ventilator use'
  # ~ pylab.title(title);
  
  # ~ sp,ax=pylab.subplots()
  # ~ color = 'tab:blue'
  # ~ ax.set_xlabel('Date')
  # ~ ax.set_ylabel('Mumbai ICU beds (7-day MA)',color=color)
  # ~ ax.plot_date(dates3,icu_used,color=color,label='ICU beds')
  # ~ ax.tick_params(axis='y', labelcolor=color)
  # ~ ax.legend(loc='lower left');
  # ~ ax2=ax.twinx()
  # ~ color = 'tab:green'
  # ~ ax2.set_ylabel('Mumbai Oxyg. beds (7-day MA)',color=color)
  # ~ ax2.plot_date(dates3,oxy_used,color=color,label='Oxygen beds')
  # ~ ax2.tick_params(axis='y', labelcolor=color)
  # ~ ax2.legend(loc='lower right');
  # ~ sp.tight_layout()
  # ~ title='Mumbai Oxygen use vs ICU use'
  # ~ pylab.title(title);

  # ~ sp,ax=pylab.subplots()
  # ~ color = 'tab:blue'
  # ~ ax.set_xlabel('Date')
  # ~ ax.set_ylabel('Mumbai actives (7-day MA)',color=color)
  # ~ ax.plot_date(dates2,actives,color=color,label='Active Cases')
  # ~ ax.tick_params(axis='y', labelcolor=color)
  # ~ ax.legend(loc='lower left');
  # ~ ax2=ax.twinx()
  # ~ color = 'tab:red'
  # ~ ax2.set_ylabel('Mumbai Daily deaths (7-day MA)',color=color)
  # ~ ax2.plot_date(dates,deaths,color=color,label='Daily deaths')
  # ~ ax2.tick_params(axis='y', labelcolor=color)
  # ~ ax2.legend(loc='lower right');
  # ~ sp.tight_layout()
  # ~ title='Mumbai active cases vs daily deaths'
  # ~ pylab.title(title);

  # ~ sp,ax=pylab.subplots()
  # ~ color = 'tab:blue'
  # ~ ax.set_xlabel('Date')
  # ~ ax.set_ylabel('Mumbai ICU percent used (7-day MA)',color=color)
  # ~ ax.plot_date(dates3,icu_pc,color=color,label='ICU utilization(%)')
  # ~ ax.tick_params(axis='y', labelcolor=color)
  # ~ ax.legend(loc='lower left');
  # ~ ax2=ax.twinx()
  # ~ color = 'tab:red'
  # ~ ax2.set_ylabel('Mumbai Daily deaths (7-day MA)',color=color)
  # ~ ax2.plot_date(dates,deaths,color=color,label='Daily deaths')
  # ~ ax2.tick_params(axis='y', labelcolor=color)
  # ~ ax2.legend(loc='lower right');
  # ~ sp.tight_layout()
  # ~ title='Mumbai ICU utilization vs daily deaths'
  # ~ pylab.title(title);
  
  # ~ sp,ax=pylab.subplots()
  # ~ color = 'tab:blue'
  # ~ ax.set_xlabel('Date')
  # ~ ax.set_ylabel('Mumbai ICU percent used (7-day MA)',color=color)
  # ~ ax.plot_date(dates3,icu_pc,color=color,label='ICU utilization(%)')
  # ~ ax.tick_params(axis='y', labelcolor=color)
  # ~ ax.legend(loc='lower left');
  # ~ ax2=ax.twinx()
  # ~ color = 'tab:red'
  # ~ ax2.set_ylabel('Mumbai Daily Deaths (7-day MA)',color=color)
  # ~ ax2.plot_date(dates,deaths,color=color,label='Daily Deaths (7-day MA)')
  # ~ ax2.tick_params(axis='y', labelcolor=color)
  # ~ ax2.legend(loc='lower right');
  # ~ sp.tight_layout()
  # ~ title='Mumbai ICU percent use vs Deaths'
  # ~ pylab.title(title);
  
  # ~ sp,ax=pylab.subplots()
  # ~ color = 'tab:blue'
  # ~ ax.set_xlabel('Date')
  # ~ ax.set_ylabel('Mumbai vent percent used (7-day MA)',color=color)
  # ~ ax.plot_date(dates3,vent_pc,color=color,label='vent utilization(%)')
  # ~ ax.tick_params(axis='y', labelcolor=color)
  # ~ ax.legend(loc='lower left');
  # ~ ax2=ax.twinx()
  # ~ color = 'tab:red'
  # ~ ax2.set_ylabel('Mumbai Daily Deaths (7-day MA)',color=color)
  # ~ ax2.plot_date(dates,deaths,color=color,label='Daily Deaths (7-day MA)')
  # ~ ax2.tick_params(axis='y', labelcolor=color)
  # ~ ax2.legend(loc='lower right');
  # ~ sp.tight_layout()
  # ~ title='Mumbai Ventilator percent use vs Deaths'
  # ~ pylab.title(title);
  
  # ~ sp,ax=pylab.subplots()
  # ~ color = 'tab:blue'
  # ~ ax.set_xlabel('Date')
  # ~ ax.set_ylabel('Mumbai vent percent used (7-day MA)',color=color)
  # ~ ax.plot_date(dates3,vent_pc,color=color,label='vent utilization(%)')
  # ~ ax.tick_params(axis='y', labelcolor=color)
  # ~ ax.legend(loc='lower left');
  # ~ ax2=ax.twinx()
  # ~ color = 'tab:orange'
  # ~ ax2.set_ylabel('Mumbai Active cases (7-day MA)',color=color)
  # ~ ax2.plot_date(dates2,actives,color=color,label='Active Cases')
  # ~ ax2.tick_params(axis='y', labelcolor=color)
  # ~ ax2.legend(loc='lower right');
  # ~ sp.tight_layout()
  # ~ title='Mumbai Ventilator utilization vs Active Cases'
  # ~ pylab.title(title);


  # ~ sp,ax=pylab.subplots()
  # ~ color = 'tab:blue'
  # ~ ax.set_xlabel('Date')
  # ~ ax.set_ylabel('Mumbai ICU beds used (7-day MA)',color=color)
  # ~ ax.plot_date(dates3,icu_used,color=color,label='Mumbai ICU beds used')
  # ~ ax.tick_params(axis='y', labelcolor=color)
  # ~ ax.legend(loc='lower left');
  # ~ ax2=ax.twinx()
  # ~ color = 'tab:red'
  # ~ ax2.set_ylabel('Mumbai Daily deaths (7-day MA)',color=color)
  # ~ ax2.plot_date(dates,deaths,color=color,label='Daily deaths')
  # ~ ax2.tick_params(axis='y', labelcolor=color)
  # ~ ax2.legend(loc='lower right');
  # ~ sp.tight_layout()
  # ~ title='Mumbai ICU beds vs daily deaths'
  # ~ pylab.title(title);

  # ~ sp,ax=pylab.subplots()
  # ~ color = 'tab:blue'
  # ~ ax.set_xlabel('Date')
  # ~ ax.set_ylabel('Mumbai vent beds used (7-day MA)',color=color)
  # ~ ax.plot_date(dates3,vent_used,color=color,label='Mumbai vent beds used')
  # ~ ax.tick_params(axis='y', labelcolor=color)
  # ~ ax.legend(loc='lower left');
  # ~ ax2=ax.twinx()
  # ~ color = 'tab:red'
  # ~ ax2.set_ylabel('Mumbai Daily deaths (7-day MA)',color=color)
  # ~ ax2.plot_date(dates,deaths,color=color,label='daily deaths')
  # ~ ax2.tick_params(axis='y', labelcolor=color)
  # ~ ax2.legend(loc='lower right');
  # ~ sp.tight_layout()
  # ~ title='Mumbai vent beds vs daily deaths'
  # ~ pylab.title(title);
  
  # ~ sp,ax=pylab.subplots()
  # ~ color = 'tab:blue'
  # ~ ax.set_xlabel('Date')
  # ~ ax.set_ylabel('Mumbai oxy beds used (7-day MA)',color=color)
  # ~ ax.plot_date(dates3,oxy_used,color=color,label='Mumbai oxy beds used')
  # ~ ax.tick_params(axis='y', labelcolor=color)
  # ~ ax.legend(loc='lower left');
  # ~ ax2=ax.twinx()
  # ~ color = 'tab:red'
  # ~ ax2.set_ylabel('Mumbai Daily deaths (7-day MA)',color=color)
  # ~ ax2.plot_date(dates,deaths,color=color,label='Daily deaths')
  # ~ ax2.tick_params(axis='y', labelcolor=color)
  # ~ ax2.legend(loc='lower right');
  # ~ sp.tight_layout()
  # ~ title='Mumbai oxy beds vs daily deaths'
  # ~ pylab.title(title);
  
  # ~ sp,ax=pylab.subplots()
  # ~ color = 'tab:blue'
  # ~ ax.set_xlabel('Date')
  # ~ ax.set_ylabel('Mumbai ICU bed capacity (7-day MA)',color=color)
  # ~ ax.plot_date(dates3,icu_cap,color=color,label='Mumbai ICU beds capacity')
  # ~ ax.tick_params(axis='y', labelcolor=color)
  # ~ ax.legend(loc='lower left');
  # ~ ax2=ax.twinx()
  # ~ color = 'tab:orange'
  # ~ ax2.set_ylabel('Mumbai actives (7-day MA)',color=color)
  # ~ ax2.plot_date(dates2,actives,color=color,label='Active cases')
  # ~ ax2.tick_params(axis='y', labelcolor=color)
  # ~ ax2.legend(loc='lower right');
  # ~ sp.tight_layout()
  # ~ title='Mumbai ICU beds vs actives'
  # ~ pylab.title(title);
  
  # ~ sp,ax=pylab.subplots()
  # ~ color = 'tab:blue'
  # ~ ax.set_xlabel('Date')
  # ~ ax.set_ylabel('Mumbai Oxygen bed utilization (7-day MA)',color=color)
  # ~ ax.plot_date(dates3,oxy_used,color=color,label='Oxygen beds Used')
  # ~ ax.tick_params(axis='y', labelcolor=color)
  # ~ ax.legend(loc='lower left');
  # ~ ax2=ax.twinx()
  # ~ color = 'tab:orange'
  # ~ ax2.set_ylabel('Mumbai Oxygen bed capacity (7-day MA)',color=color)
  # ~ ax2.plot_date(dates3,oxy_cap,color=color,label='Oxygen beds capacity')
  # ~ ax2.tick_params(axis='y', labelcolor=color)
  # ~ ax2.legend(loc='lower right');
  # ~ sp.tight_layout()
  # ~ title='Mumbai Oxygen beds used vs Oxygen Beds capacity'
  # ~ pylab.title(title);
  
  # ~ sp,ax=pylab.subplots()
  # ~ color = 'tab:blue'
  # ~ ax.set_xlabel('Date')
  # ~ ax.set_ylabel('Mumbai ICU bed utilization (7-day MA)',color=color)
  # ~ ax.plot_date(dates3,icu_used,color=color,label='ICU beds Used')
  # ~ ax.tick_params(axis='y', labelcolor=color)
  # ~ ax.legend(loc='lower left');
  # ~ ax2=ax.twinx()
  # ~ color = 'tab:orange'
  # ~ ax2.set_ylabel('Mumbai ICU bed capacity (7-day MA)',color=color)
  # ~ ax2.plot_date(dates3,icu_cap,color=color,label='ICU beds capacity')
  # ~ ax2.tick_params(axis='y', labelcolor=color)
  # ~ ax2.legend(loc='lower right');
  # ~ sp.tight_layout()
  # ~ title='Mumbai ICUs used vs ICUs capacity'
  # ~ pylab.title(title);
  
  # ~ sp,ax=pylab.subplots()
  # ~ color = 'tab:blue'
  # ~ ax.set_xlabel('Date')
  # ~ ax.set_ylabel('Mumbai vent bed utilization (7-day MA)',color=color)
  # ~ ax.plot_date(dates3,vent_used,color=color,label='vent beds Used')
  # ~ ax.tick_params(axis='y', labelcolor=color)
  # ~ ax.legend(loc='lower left');
  # ~ ax2=ax.twinx()
  # ~ color = 'tab:orange'
  # ~ ax2.set_ylabel('Mumbai vent bed capacity (7-day MA)',color=color)
  # ~ ax2.plot_date(dates3,vent_cap,color=color,label='vent beds capacity')
  # ~ ax2.tick_params(axis='y', labelcolor=color)
  # ~ ax2.legend(loc='lower right');
  # ~ sp.tight_layout()
  # ~ title='Mumbai Ventilators used vs Ventilators capacity'
  # ~ pylab.title(title);
  
  # ~ sp,ax=pylab.subplots()
  # ~ color = 'tab:blue'
  # ~ ax.set_xlabel('Date')
  # ~ ax.set_ylabel('Mumbai ICU beds used (7-day MA)',color=color)
  # ~ ax.plot_date(dates3,icu_used,color=color,label='Mumbai ICU beds used')
  # ~ ax.tick_params(axis='y', labelcolor=color)
  # ~ ax.legend(loc='lower left');
  # ~ ax2=ax.twinx()
  # ~ color = 'tab:orange'
  # ~ ax2.set_ylabel('Mumbai actives (7-day MA)',color=color)
  # ~ ax2.plot_date(dates2,actives,color=color,label='Active cases')
  # ~ ax2.tick_params(axis='y', labelcolor=color)
  # ~ ax2.legend(loc='lower right');
  # ~ sp.tight_layout()
  # ~ title='Mumbai ICU beds vs actives'
  # ~ pylab.title(title);

  # ~ sp,ax=pylab.subplots()
  # ~ color = 'tab:blue'
  # ~ ax.set_xlabel('Date')
  # ~ ax.set_ylabel('Mumbai vent beds used (7-day MA)',color=color)
  # ~ ax.plot_date(dates3,vent_used,color=color,label='Mumbai vent beds used')
  # ~ ax.tick_params(axis='y', labelcolor=color)
  # ~ ax.legend(loc='lower left');
  # ~ ax2=ax.twinx()
  # ~ color = 'tab:orange'
  # ~ ax2.set_ylabel('Mumbai actives (7-day MA)',color=color)
  # ~ ax2.plot_date(dates2,actives,color=color,label='Active cases')
  # ~ ax2.tick_params(axis='y', labelcolor=color)
  # ~ ax2.legend(loc='lower right');
  # ~ sp.tight_layout()
  # ~ title='Mumbai vent beds vs actives'
  # ~ pylab.title(title);
  
  # ~ sp,ax=pylab.subplots()
  # ~ color = 'tab:blue'
  # ~ ax.set_xlabel('Date')
  # ~ ax.set_ylabel('Mumbai oxy beds used (7-day MA)',color=color)
  # ~ ax.plot_date(dates3,oxy_used,color=color,label='Mumbai oxy beds used')
  # ~ ax.tick_params(axis='y', labelcolor=color)
  # ~ ax.legend(loc='lower left');
  # ~ ax2=ax.twinx()
  # ~ color = 'tab:orange'
  # ~ ax2.set_ylabel('Mumbai actives (7-day MA)',color=color)
  # ~ ax2.plot_date(dates2,actives,color=color,label='Active cases')
  # ~ ax2.tick_params(axis='y', labelcolor=color)
  # ~ ax2.legend(loc='lower right');
  # ~ sp.tight_layout()
  # ~ title='Mumbai oxy beds vs actives'
  # ~ pylab.title(title);
  

  
  
def karnataka_parse_csv(old=False):
  import csv;info=[]
  if old:
    r=csv.reader(open('csv_dumps/karnataka_fatalities_details_jul16_sep10.csv'))
  else:
    r=csv.reader(open('csv_dumps/karnataka_fatalities_truncated_Feb15_May05.csv'))
  for i in r: info.append(i);
  info=info[1:];fatalities=[]
  try: assert(global_karnataka_case_series!='')
  except AssertionError:
    print('For ka parse csv to work, global_karnataka_case_series must be defined')
  for row in info[2:]:
    try:
      patient_number=row[0]
      district=row[1];
      age=row[2];gender=row[3];origin=row[4];date_of_detection=row[5];date_of_admission=row[6];date_of_death=row[7];
      bulletin_date=row[8];comorbidity=','.join(row[9:])
      # ~ print comorbidity
      date_of_admission=datetime.datetime.strptime(date_of_admission,'%Y-%m-%d')
      date_of_death=datetime.datetime.strptime(date_of_death,'%Y-%m-%d')
      bulletin_date=datetime.datetime.strptime(bulletin_date,'%Y-%m-%d')
      fatality=generic_fatality(district,patient_number,age,gender,origin,comorbidity,date_of_admission,date_of_death,bulletin_date)
      fatalities.append(fatality)
    except:
      print('could not process csv_row '+str(row));return
  return fatalities

def mode1(x):
  values,counts=np.unique(x, return_counts=True)
  m=counts.argmax()
  # ~ return values[m],counts[m]
  return values[m]
def simplify_json():
  x=json.load(open('state_test_data.json'))['states_tested_data']
  x2=[]
  for d in x:
    d2=d.copy()
    for k in d:
      if not d[k]: d2.pop(k)
    x2.append(d2)
  x={'states_tested_data': x2}
  a=open('simplified.json','w')
  json.dump(x,a);a.close()
  print('wrote simplified.json from state_test_data.json removing empty fields')

def predict_vaccination_effect(state='Karnataka',percent_type='percetn45plus',base=85,delay=7,pop_multiple=1.15):
  if len(state)==2 and state in state_code_to_name: x=state;state=state_code_to_name[state];#print('expanded %s to %s' %(x,state))
  y=helper_get_mean_deaths(filter_type=percent_type,date_type='admission',state=state)#,startdate=datetime.date(2021,3,1,0,0))
  datesd,pd45plus=zip(*y)
  dates,v,v2,p60plus,p45plus=zip(*karnataka_parse_vaccination(multiple=pop_multiple))
  puv=100-np.array(p45plus)
  
  rem=100-base
  baserem=puv*0.01*base
  predicted_pd=100*(baserem/(baserem+rem))
  #add delay
  orig_len=len(predicted_pd)  
  predicted_pd=np.concatenate((np.ones(delay)*base,predicted_pd))[:orig_len]
  
  # ~ plot2(datesd,pd45plus,dates,predicted_pd,label1='percent of 45+ in daily deaths',label2='PREDICTION for percent of 45+ in daily deaths',color2='cyan',draw_vline=True)
  sp,ax=pylab.subplots()
  
  locator = mdates.AutoDateLocator(minticks=3, maxticks=7);  formatter = mdates.ConciseDateFormatter(locator)
  ax.xaxis.set_major_locator(locator);  ax.xaxis.set_major_formatter(formatter) 
  
  ax.set_xlabel('Date');ax.set_ylabel('percent of 45+ in daily deaths')
  #HACK
  datesd=datesd[:-4];pd45plus=pd45plus[:-4]
  ax.plot_date(datesd,pd45plus,color='blue',label='percent of 45+ in daily deaths')
  
  ax.vlines(pylab.date2num([datetime.datetime(2021, 3, 1, 0, 0)]),min(pd45plus)-0.5,max(pd45plus)+0.5,label='Elderly vaccinations begin',color='green',linestyles='dashed',linewidth=4)
  
  ax.plot_date(dates,predicted_pd,color='cyan',label='PREDICTIOn for percent of 45+ in daily deaths')
  ax.legend()
  title='Prediction vs Actual for Karnataka daily deaths'
  pylab.title(title);  pylab.savefig(TMPDIR+title+'.jpg',dpi=100);pylab.close();print('saved '+TMPDIR+title+'.jpg')
  
  
def helper_get_mean_deaths(deaths='',filter_type='',date_type='',moving_average=True,ma_size=7,state='Tamil Nadu',plot=True,draw_vline=True,startdate=datetime.date(2021,3,1),enddate=datetime.date(2021,5,18),skip_plot_date='',plot_linear_fit=True,use_median=False,ignore_capital=True,capital_district='',find_cis=False,special_title=''):
  if len(state)==2 and state in state_code_to_name: x=state;state=state_code_to_name[state];#print('expanded %s to %s' %(x,state))
  if filter_type in ['p60','p60p','p60plus']: filter_type='percent60plus'
  if filter_type in ['p45','p45p','p45plus']: filter_type='percent45plus'
  if not deaths:
    if state=='Tamil Nadu': deaths=tamil_nadu_parse_csv() ;print('loaded TN fatality data from csv')
    elif state=='Kerala': deaths=kerala_parse_csv();print('loaded KL fatality data from csv')
    elif state=='Karnataka': deaths=karnataka_parse_csv();print('loaded KA fatality data from csv')
    elif state=='Chhattisgarh': deaths=chhattisgarh_parse_csv();print('loaded CT fatality data from csv')
    else: print('State is not TN/KL and no deaths data given to function');return
  import scipy.stats as st;import statsmodels.api as sm
  d1=startdate
  d2=enddate
  delta=d2-d1
  datetimes=[(d1 + datetime.timedelta(days=i)) for i in range(delta.days + 1)]
  datetimes=[datetime.datetime.combine(i,datetime.time(0, 0)) for i in datetimes]
  if skip_plot_date:
    skip_plot_date=datetime.datetime.combine(skip_plot_date,datetime.time(0, 0))
  # ~ return datetimes

  mean_values=[];capital='bengaluru';outside=''
  
  ma_delta=datetime.timedelta(days=ma_size)
  if state=='Tamil Nadu':capital='chennai';outside='RoTN'
  elif state=='Kerala':capital='Thiruvananthapuram';outside='RoKL'
  elif state=='Karnataka':capital='Bengaluru';outside='RoKA'
  
  if capital_district: capital=capital_district;print('setting capital to '+capital_district)

  for dd in datetimes:
    d='';d1='';d2=''
    if moving_average:
      if not date_type or date_type=='death': #default behavious
        d=[i for i in deaths if i.date_of_death<=dd and i.date_of_death>=(dd-ma_delta)]
        if not ignore_capital:
          d1=[i for i in deaths if i.date_of_death<=dd and i.date_of_death>=(dd-ma_delta) and i.district==capital]
          d2=[i for i in deaths if i.date_of_death<=dd and i.date_of_death>=(dd-ma_delta) and i.district!=capital]
        
         
      elif date_type=='reporting':
        d=[i for i in deaths if i.date_of_reporting and i.date_of_reporting<=dd and i.date_of_reporting>=(dd-ma_delta)]
        if not ignore_capital:
          d1=[i for i in deaths if i.date_of_reporting and i.date_of_reporting<=dd and i.date_of_reporting>=(dd-ma_delta) and i.district==capital]
          d2=[i for i in deaths if i.date_of_reporting and i.date_of_reporting<=dd and i.date_of_reporting>=(dd-ma_delta) and i.district!=capital]
        
          
      elif date_type=='admission':
        d=[i for i in deaths if i.date_of_admission<=dd and i.date_of_admission>=(dd-ma_delta)]
        if not ignore_capital:
          d1=[i for i in deaths if i.date_of_admission<=dd and i.date_of_admission>=(dd-ma_delta) and i.district==capital]
          d2=[i for i in deaths if i.date_of_admission<=dd and i.date_of_admission>=(dd-ma_delta) and i.district!=capital]
  
    else:
      d=[i for i in deaths if i.date_of_death==dd]
      if not ignore_capital:
        d1=[i for i in deaths if i.date_of_death==dd and i.district==capital]
        d2=[i for i in deaths if i.date_of_death==dd and i.district!=capital]
  
    m1=0;m2=0
    
    if filter_type=='gender': #find fraction of males in daily deaths on date
      if d: d=100*float(len([i for i in d if i.gender=='M']))/len(d)
      else: d=0
      if not ignore_capital:
        if d1: d1=100*float(len([i for i in d1 if i.gender=='M']))/len(d1)
        else: d1=0
        if d2: d2=100*float(len([i for i in d2 if i.gender=='M']))/len(d2)
        else: d2=0
    elif filter_type=='origin': #find fraction of SARI/ILI in daily deaths on date
      d=100*float(len([i for i in d if i.origin in ['SARI','ILI']]))/len(d)
      if not ignore_capital:
        d1=100*float(len([i for i in d1 if i.origin in ['SARI','ILI']]))/len(d1)
        d2=100*float(len([i for i in d2 if i.origin in ['SARI','ILI']]))/len(d2)
    elif filter_type=='percent60plus': #find fraction of SARI/ILI in daily deaths on date
      if d: 
        x1=len([i for i in d if i.age>=60])
        tot=len(d)
        if find_cis:
          cis=100*np.array(sm.stats.proportion_confint(x1,tot))
          
        d=100*float(x1)/tot
      else: d=0
      if not ignore_capital:
        if d1: d1=100*float(len([i for i in d1 if i.age>=60]))/len(d1)
        else: d1=0
        if d2: d2=100*float(len([i for i in d2 if i.age>=60]))/len(d2)
        else: d2=0
    elif filter_type=='percent45plus': #find fraction of SARI/ILI in daily deaths on date
      if d: 
        x1=len([i for i in d if i.age>=45])
        tot=len(d)
        if find_cis:
          cis=100*np.array(sm.stats.proportion_confint(x1,tot))
        d=100*float(x1)/tot
      else: d=0
      if not ignore_capital:
        if d1: d1=100*float(len([i for i in d1 if i.age>=45]))/len(d1)
        else: d1=0
        if d2: d2=100*float(len([i for i in d2 if i.age>=45]))/len(d2)
        else: d2=0
    elif filter_type=='percentupto45': #find fraction of SARI/ILI in daily deaths on date
      if d: 
        d=100*float(len([i for i in d if i.age<45]))/len(d)
      else: d=0
      if not ignore_capital:
        if d1: d1=100*float(len([i for i in d1 if i.age<45]))/len(d1)
        else: d1=0
        if d2: d2=100*float(len([i for i in d2 if i.age<45]))/len(d2)
        else: d2=0
    elif filter_type=='percent45to60': #find fraction of SARI/ILI in daily deaths on date
      if d: d=100*float(len([i for i in d if i.age>=45 and i.age<60]))/len(d)
      # ~ if d: d=100*float(len([i for i in d if i.age>=45 and i.age<60]))/len([i for i in d if i.age<60])
      else: d=0
      if not ignore_capital:
        if d1: d1=100*float(len([i for i in d1 if i.age>=45 and i.age<60]))/len(d1)
        else: d1=0
        if d2: d2=100*float(len([i for i in d2 if i.age>=45 and i.age<60]))/len(d2)
        else: d2=0
    elif filter_type=='comorb': #find fraction of SARI/ILI in daily deaths on date
      d=100*float(len([i for i in d if i.comorbidities!=['']]))/len(d)
      if not ignore_capital:
        d1=100*float(len([i for i in d1 if i.comorbidities!=['']]))/len(d1)
        d2=100*float(len([i for i in d2 if i.comorbidities!=['']]))/len(d2)
    elif filter_type=='comorb45to60': #find fraction of SARI/ILI in daily deaths on date
      d=[i for i in d if i.age>=45 and i.age<60]
      if not ignore_capital:
        d1=[i for i in d1 if i.age>=45 and i.age<60]
        d2=[i for i in d2 if i.age>=45 and i.age<60]
      if d: d=100*float(len([i for i in d if i.comorbidities!=['']]))/len(d)
      else: d=0
      if not ignore_capital:
        if d1: d1=100*float(len([i for i in d1 if i.comorbidities!=['']]))/len(d1)
        else: d1=0
        if d2: d2=100*float(len([i for i in d2 if i.comorbidities!=['']]))/len(d2)
        else: d2=0
    elif filter_type=='admission_death': #find fraction of SARI/ILI in daily deaths on date
      d=[i.admission_death_interval for i in d if i.admission_death_interval>=0]
      if not ignore_capital:
        d1=[i.admission_death_interval for i in d1 if i.admission_death_interval>=0]
        d2=[i.admission_death_interval for i in d2 if i.admission_death_interval>=0]
    elif filter_type=='death_reporting': #find fraction of SARI/ILI in daily deaths on date
      d=[i.death_reporting_interval for i in d if i.death_reporting_interval and i.death_reporting_interval>=0]
      if not ignore_capital:
        d1=[i.death_reporting_interval for i in d1 if i.death_reporting_interval and i.death_reporting_interval>=0]
        d2=[i.death_reporting_interval for i in d2 if i.death_reporting_interval and i.death_reporting_interval>=0]
    elif filter_type=='raw_number': #find raw_number of deaths
      if moving_average:
        d=float(len(d))/(ma_size)
        if not ignore_capital:
          d1=float(len(d1))/(ma_size)
          d2=float(len(d2))/(ma_size)
      else:
        d=float(len(d))
        if not ignore_capital:
          d1=float(len(d1))
          d2=float(len(d2))
    elif filter_type in ['mean_age_male']: #find raw_number of deaths
      d=[i.age for i in d if i.gender=='M']
      if not ignore_capital:
        d1=[i.age for i in d1 if i.gender=='M']
        d2=[i.age for i in d2 if i.gender=='M']
    elif filter_type in ['mean_age_female']: #find raw_number of deaths
      d=[i.age for i in d if i.gender=='F']
      if not ignore_capital:
        d1=[i.age for i in d1 if i.gender=='F']
        d2=[i.age for i in d2 if i.gender=='F']
      
    elif filter_type=='raw_number_under45': #find raw_number of deaths
      d=[i for i in d if i.age<45]
      if not ignore_capital:
        d1=[i for i in d1 if i.age<45]
        d2=[i for i in d2 if i.age<45]
        
      if moving_average:
        d=float(len(d))/(ma_size)
        if not ignore_capital:
          d1=float(len(d1))/(ma_size)
          d2=float(len(d2))/(ma_size)
      else:
        d=float(len(d))
        if not ignore_capital:
          d1=float(len(d1))
          d2=float(len(d2))
    else: #find all ages on date
      d=[i.age for i in d]
      if not ignore_capital:
        d1=[i.age for i in d1]
        d2=[i.age for i in d2]

    if filter_type in ['gender','origin','comorb','comorb45to60','raw_number']: #find percent of males in daily deaths over time
      if not ignore_capital:
        mean_values.append((dd,d,d1,d2))
      else:
        mean_values.append((dd,d))
    else:
      if not d:
        # ~ print 'no deaths info for '+str(dd)
        continue
      m=0;m1=0;m2=0

      if use_median:
        # ~ print('using median not mean')
        if not ignore_capital:
          if d1: m1=np.median(d1)
          if d2: m2=np.median(d2)
        if d: m=np.median(d)
      else:
        if not ignore_capital:
          if d1: m1=numpy.mean(d1)
          if d2: m2=numpy.mean(d2)
        if d: 
          m=numpy.mean(d)
          # ~ print(d),print(m)
          if find_cis and filter_type in ['']:
            cis=[]
            if type(d)==list:
              cis=st.t.interval(0.95, len(d)-1, loc=np.mean(d), scale=st.sem(d))
              # ~ cis=d
      if m :
        if not ignore_capital:          
          mean_values.append((dd,m,m1,m2))
        else:
          if find_cis and ((type(cis)==numpy.ndarray and cis.any()) or cis):
            mean_values.append((dd,m,cis))
          else:
            mean_values.append((dd,m))
      # ~ print('got for %s' %(dd.strftime('%d-%m')))
  if plot:
    pylab.close()
    # ~ mean_values=mean_values[:-5]
    if filter_type=='death_reporting': 
      mean_values=mean_values[:-5]
      mean_values=[i for i in mean_values if i[1]<4 and (i[0]>=datetime.datetime(2020,9,20,0,0) or i[0]<=datetime.datetime(2020,9,7,0,0)) ] #temp hack
    try:
      if not ignore_capital:
        dates,m,m1,m2=zip(*mean_values)
      else:
        if find_cis:
          dates,m,cis=zip(*mean_values)
        else:
          dates,m=zip(*mean_values)
    except: 
      print(mean_values);return
    xlabel='';ylabel='';title=''
    if date_type=='':      xlabel='Date of death'
    elif date_type=='admission':      xlabel='Date of admission'
    elif date_type=='reporting':      xlabel='Date of reporting'
    ax=pylab.axes()
    locator = mdates.AutoDateLocator(minticks=3, maxticks=7)
    # ~ formatter = mdates.ConciseDateFormatter(locator)
    formatter = mdates.ConciseDateFormatter(locator)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(formatter) 

    if filter_type=='':      
      label='Mean age'
      if use_median: label='Median Age'
    elif filter_type=='mean_age_male':      label='Mean age of Males in daily deaths'
    elif filter_type=='mean_age_female':      label='Mean age of Females in daily deaths'
    elif filter_type=='gender':      label='Percentage of Males in daily deaths'
    elif filter_type=='comorb':      label='Percentage of deaths with comorbidities among daily deaths'
    elif filter_type=='comorb45to60':      label='Percent of deaths with comorbidities(45-60 yrs)'
    elif filter_type=='admission_death':      label='Admission-Death interval'
    elif filter_type=='death_reporting':      label='Death-Reporting interval'
    elif filter_type=='percent60plus':      label='Percent of deaths that were 60+yrs'
    elif filter_type=='percent45to60':      label='Percent of deaths that were 45-60 yrs'
    elif filter_type=='percent45plus':      label='Percent of deaths that were 45+ yrs'
    elif filter_type=='percentupto45':      label='Percent of deaths that were upto 45 yrs'
    elif filter_type=='raw_number':      label='Raw number of deaths'
    elif filter_type=='raw_number_under45':      label='Raw number of deaths (under 45 yrs)'
    label+=' (7-day MA)'
    
    if skip_plot_date:
      xx=list(zip(dates,m))
      xx=[i for i in xx if i[0]>=skip_plot_date]
      # ~ print(xx);print(skip_plot_date)
      dates,m=zip(*xx)
    #mean age vs time
    ax.plot_date(pylab.date2num(dates),m,label=label);
    if find_cis:
      ci0=[i[0] for i in cis]
      ci1=[i[1] for i in cis]
      ax.fill_between(pylab.date2num(dates), ci0, ci1, color='grey', alpha=.25,label='95% CI') 
      # ~ for idx in range(len(dates)):
        # ~ date=pylab.date2num(dates[idx]);
        # ~ ci=cis[idx]
        # ~ if len(ci)>1:
          # ~ ax.fill_between(date, ci[0], ci[1], color='grey', alpha=.1) 
          # ~ try: ax.fill_between(date, ci[0], ci[1], color='grey', alpha=.1) 
          # ~ except: print('ci plot failed for '+str(idx)) 
    title=label+' for '+state
    pylab.xlabel(xlabel);pylab.ylabel(label);pylab.title(title);
    if plot_linear_fit:
      helper_plot_linear_fit(pylab.date2num(dates),m);
    
    
    if draw_vline:
      if find_cis:
        ci0=[i[0] for i in cis]
        ci1=[i[1] for i in cis]
        pylab.vlines(pylab.date2num([datetime.datetime(2021, 3, 1, 0, 0)]),min(ci0),max(ci1),color='xkcd:rose',label='Elderly vaccinations begin',linestyle='dashed',linewidth=4)
      else:
        pylab.vlines(pylab.date2num([datetime.datetime(2021, 3, 1, 0, 0)]),min(m),max(m),color='xkcd:rose',label='Elderly vaccinations begin',linestyle='dashed',linewidth=4)

    ax.legend(fontsize=7)
    pylab.savefig(TMPDIR+title+'.jpg');#pylab.show();
    print('saved '+TMPDIR+title+'.jpg')
    pylab.close()
    
    if not ignore_capital:

      ax=pylab.axes()
      locator = mdates.AutoDateLocator(minticks=3, maxticks=7)
      formatter = mdates.ConciseDateFormatter(locator)
      ax.xaxis.set_major_locator(locator)
      ax.xaxis.set_major_formatter(formatter) 
  
      #chn and rotn
      ax.plot_date(pylab.date2num(dates),m1,label=label+'('+capital+')');
      # ~ ax.plot_date(pylab.date2num(dates),m2,label=label+' ('+outside+')');
      ax.plot_date(pylab.date2num(dates),m,label=label+' ('+state+')');
      # ~ title=label+' for '+capital+' and '+outside+' (over time)'
      title=label+' for '+capital+' and '+state+' (over time)'
      pylab.xlabel(xlabel);pylab.ylabel(label);pylab.title(title);
      ax.legend(fontsize=7)
      pylab.savefig(TMPDIR+title+'.jpg');pylab.close()

  # ~ print('returning mean_v')
  return mean_values

def kerala_parse_deaths(format_type='new'):  
  b=[]
  if os.path.exists('olddeaths.txt'):  b=[i.strip() for i in open('olddeaths.txt').readlines() if i.strip()][3:]
  patient_numbers=[i.strip().split()[0] for i in b if i.strip()[0].isdigit()]
  districts=[i.split()[1] for i in b if i.strip()[0].isdigit()]
  ages=[i.split()[2] for i in b if i.strip()[0].isdigit()]
  dods=[i.replace('Comorbidity present','').replace('-','').replace('Import','').replace('import','').replace('Contact','').replace('Nil','').strip().split()[-1] for i in b if i.strip()[0].isdigit()]
  dods=[i[:2]+'-'+i[2:4]+'-'+i[4:6]+'20' for i in dods]

  fatalities=[];critical=[];comm=[]
  
  for j in range(len(ages)):
    dod0=datetime.datetime.strptime(dods[j],'%d-%m-%Y')
    f=generic_fatality(districts[j],patient_numbers[j],ages[j],'','','','',dod0,'',state='Kerala')
    fatalities.append(f)

  if format_type=='old':    return fatalities

  pdfs=[i for i in os.listdir('.') if i.endswith('.pdf')];pdfs.sort()
  if not pdfs: print('no pdf files(kerala bulletins) in curdir!!');return
  for pdf in pdfs:
    print(('parsing '+pdf))
    cmd='pdftotext -nopgbrk -layout "'+pdf+'" tmp.txt';os.system(cmd)
  
    # ~ b=[i.strip() for i in open('tmp.txt').readlines() if i.strip()][3:]
    b=[i.strip() for i in open('tmp.txt','r',encoding='unicode_escape').readlines() if i.strip()][3:]
    bulletin_date=[i for i in b if i.startswith('Date:')]
    if not bulletin_date:
      print(('could not find date from bulletin: '+bulletin+' !!'))
      return
    bulletin_date=bulletin_date[0].split(':')[1].strip()
    bulletin_date=datetime.datetime.strptime(bulletin_date.replace('.','/').replace('-','/'),'%d/%m/%Y')
  
    indices=[];idx=0
    for i in b:
      if i.startswith(('Table 6','Table 7','Table 8','Table 9')): indices.append(idx)
      idx+=1
  
    contact_cases=b[indices[0]:indices[1]]
    death_details=b[indices[1]:indices[2]]
    icu=b[indices[2]:indices[3]]
  
    #cases of community transmission
    percent_unknown_origin=0;tot='';unk=''
    tot=[i for i in contact_cases if 'Total cases' in i]
    if tot: tot=tot[0].strip().split()[-1]
    if tot.isdigit(): tot=float(tot)
  
    unk=[i for i in contact_cases if 'no history of' in i]
    if unk: unk=unk[0].strip().split()[-1]
    if unk.isdigit(): unk=float(unk)
  
    if tot and unk:
      percent_unknown_origin=100*(unk/tot)
    else:
      print(('could not find Total cases and iunk in bulletin: '+bulletin))
      return

    comm.append(kerala_community_tr(bulletin_date,percent_unknown_origin))

    #death details
    entries=[i for i in death_details if i.strip()[0].isdigit()]
    for entry in entries:
      if len(entry.split())==1: continue #empty row
      try:
        district=entry.split()[1].strip()
      except:
        print(('error getting district with enrty: '+entry))
        return
  
      age=entry.split()[2].strip()
      if ('month' in entry.split()[3].lower()) or ('month' in entry.split()[2].lower()): age='1'
  
      gender=entry.split()[-3].strip()
      if gender.lower()=='female': gender='F'
      else: gender='M'
  
      dod=entry.split()[-2].strip().replace('267.09.2020','26.09.2020').replace('.','/').replace('2021','2021').replace('2O21','2021').replace('-','/').replace('202I','2021').replace('/221','/2021').replace('/20210','/2021').replace('/052021','/05/2021').replace('/O5/','/05/')
      if '00/01/1900' in dod: print('unparsable 1900 date.continuing.');continue
      if dod.count('/')==2:
        if dod.endswith('/20'):dod+='20'
        elif dod.endswith('/21'):dod=dod.replace('/21','/2021')
        # ~ dod=dod.replace('/221','/2021').replace('/052021','/05/2021')
        try: dod=datetime.datetime.strptime(dod,'%d/%m/%Y')
        except:
          print('could not converet dod: ',dod);return
  
      origin=entry.split()[-1].strip()
      if origin.lower()=='contact': origin='CONT'
      # ~ district,patient_number,age,gender,origin,comorbidity,date_of_admission,date_of_death,bulletin_date,state='Karnataka'
      f=generic_fatality(district,'',age,gender,origin,'','',dod,bulletin_date,state='Kerala')
      fatalities.append(f)
  
    #get icu use
    icu_patients=[i for i in icu if 'in ICU' in i]
    if icu_patients: icu_patients=int(icu_patients[0].strip().split()[-1])
  
    ventilator_patients=[i for i in icu if 'on Ventilator' in i]
    if ventilator_patients: ventilator_patients=int(ventilator_patients[0].strip().split()[-1])
  
    critical_obj=generic_icu_usage(bulletin_date,'',icu_patients,ventilator_patients)
    critical.append(critical_obj)
  
  return comm,fatalities,critical
  
def chhattisgarh_parse_csv():
  r=csv.reader(open('csv_dumps/CT_fatalities_Feb_May_2021.csv'))
  info=[];
  for i in r: 
    if i: info.append(i)
  info=info[1:]
  x=[]
  for entry in info:
    try:
      date_of_admission=datetime.datetime.strptime(entry[1].strip()+'/2021','%d/%m/%Y')
    except:
      print('unable to get doa from '+str(entry))
      return
    age=entry[0].strip()
    
    f=generic_fatality('','',age,'','','',date_of_admission,'','')
    x.append(f)
    
  return x
def karnataka_parse_deaths(bulletin='09_09_2020.pdf',bulletin_date=datetime.datetime(2020, 9, 9, 0, 0),page_range='',stop_debug=''):
  if stop_debug and (not page_range): #means coming from debug
    (bulletin_date,annex_range)=karnataka_bulletin_parser(bulletin,return_date_only=True)
    page_range=annex_range['deaths']
    
  start_page=str(page_range[0])
  end_page=str(page_range[1])

  margins=karnataka_bulletin_get_margins(bulletin,page_range)
  if not margins and stop_debug:
    print(('no margins found with page_range: '+str(page_range)))

  format_type=1;#means place column exists
  if 'place' not in margins: format_type=0;#place colum does not exist

  #get districts name
  districts=[]
  x=str(margins['district'][0]);w=str(margins['district'][1]); #for new
  cmd='pdftotext -x '+x+'  -W '+w+' -y 0 -H 1000  -nopgbrk -layout -f '+start_page+' -l '+end_page+' '+bulletin+' tmp.txt';os.system(cmd);
  b=[i.strip() for i in open('tmp.txt').readlines() if i.strip().lower().startswith(tuple(karnataka_districts_map.keys()))]

  districts=[helper_map_district_start_char_to_fullname(i) for i in b]

  if stop_debug=='district':
    print('stopping after getting district info')
    return districts,b

  #p.no,gender,age,origin
  x=str(margins['spnotodesc'][0]);w=str(margins['spnotodesc'][1]); #for new
  cmd='pdftotext -x '+x+'  -W '+w+' -y 0 -H 1000  -nopgbrk -layout -f '+start_page+' -l '+end_page+' '+bulletin+' tmp.txt';os.system(cmd);
  b0=[i.strip() for i in open('tmp.txt').readlines() if i.strip()]
  b=[i.strip() for i in b0 if i.strip()[0].isdigit()]
  b=[i for i in b if len(i)>6];#check for minimum length

  patient_numbers=[];ages=[];genders=[];origins=[];idx=-1
  for i in b:
    idx+=1
    if len(i.split())<4:      
      #HACK for error for "contact of P-18548" etc
      last_entry=b0[b0.index(i)-1]
      if stop_debug=='origin':
        print(('when parsing origin, field in b was less than 4 for: '+i+' last_entr: '+last_entry))
        
      if last_entry.lower().startswith(('contact','ct of','asymp','under','sari','ili','e from')):
        patient_number=i.split()[0];age=i.split()[1];gender=i.split()[2]
        if last_entry.lower().startswith(('contact','ct of','e from')): origin='CONT'
        elif last_entry.lower().startswith('asymp'): origin='ASYM'
        elif last_entry.lower().startswith('under'): origin='UNKN'
        elif last_entry.lower().startswith('sari'): origin='SARI'
        elif last_entry.lower().startswith('ILI'): origin='ILI'
        if age.lower().startswith('mont'):age='1'
        patient_numbers.append(patient_number);ages.append(age);genders.append(gender);origins.append(origin)
      
      elif last_entry.lower().startswith('mo'):#age is in months
        patient_number=i.split()[0];gender=i.split()[1]
        origin=i.split()[2];age='1'
        patient_numbers.append(patient_number);ages.append(age);genders.append(gender);origins.append(origin)
      elif last_entry.lower().startswith(('mal','fem','ma')):#malformed gender data
        patient_number=i.split()[0];age=i.split()[1]
        origin=i.split()[2];
        if last_entry.lower().startswith('ma'): gender='M'
        elif last_entry.lower().startswith('fem'): gender='F'
        patient_numbers.append(patient_number);ages.append(age);genders.append(gender);origins.append(origin)
      
      continue; #need all fields
    patient_number=i.split()[0];age=i.split()[1]
    gender=i.split()[2];origin=i.split()[3]
    if 'under' in origin or 'contact' in origin or 'trac' in origin: origin='CONT'
    if age.lower().startswith('mont'):age='1'
    patient_numbers.append(patient_number);ages.append(age);genders.append(gender);origins.append(origin)

  if stop_debug=='origin':
    print('stopping after getting origin info')
    return districts,patient_numbers,ages,genders,origins,b
    
  #comorbidities
  x=str(margins['comorb'][0]);w=str(margins['comorb'][1]); #for new
  cmd='pdftotext -x '+x+'  -W '+w+' -y 0 -H 1000  -nopgbrk -layout -f '+start_page+' -l '+end_page+' '+bulletin+' tmp.txt';os.system(cmd);
  
  b=[i.strip() for i in open('tmp.txt').readlines() if i.strip() and (i.strip() in ['-','_','--'] or i.strip()[0].isupper())]
  b=[i.replace('EPILEPSY','EPL').replace('Epilepsy','EPL') for i in b]; #workarounds
  b=[i for i in b if (len(i.split(',')[0])<6 and not i.startswith('Co')) or ('neumo' in i.lower() or 'eptic' in i.lower() or 'carci' in i.lower() or 'asthma' in i.lower() or 'nemia' in i.lower() or 'naemia' in i.lower() or 'besity' in i.lower() or 'sepsis' in i.lower() )] #workarounds
  if bulletin=='08_30_2020.pdf':#workarounds for malformed bulletin
    b=[i.replace('HTN, CKD,','HTN, CKD') for i in b]; 
  
  comorbidities=[];comorbidity=''
  for i in b:
    # ~ print i
    if i in ['-','_','--']:
      if comorbidity:
        if comorbidity.endswith(','):comorbidity=comorbidity[:-1]
        comorbidities.append(comorbidity); #HACK. sometimes last term still ends in ",", but next elem is "-"
      comorbidities.append('NONE')
      comorbidity=''
    elif i.endswith(','):
      comorbidity+=i
    else:
      comorbidity+=i
      comorbidities.append(comorbidity)
      comorbidity=''
  if bulletin=='08_25_2020.pdf':#workarounds for malformed bulletin
    comorbidities.insert(77,'NONE')
    comorbidities[135]='DM,HTN'    
    comorbidities.insert(136,'DM,HTN')
    comorbidities.insert(136,'DM,HTN,IHD,CKD')
  elif bulletin=='08_24_2020.pdf':#workarounds for malformed bulletin
    comorbidities.insert(12,'NONE')
  elif bulletin=='08_17_2020.pdf':#workarounds for malformed bulletin
    comorbidities.insert(68,'NONE')
    comorbidities.insert(73,'NONE')
    comorbidities[73]='DM, HTN';comorbidities[74]='NONE'
    
  #HACK for carcinoma
  for occ in range(comorbidities.count('OMA')): comorbidities.remove('OMA')
  
  if stop_debug=='comorb':
    print('stopping after getting comorb info')
    return districts,patient_numbers,ages,genders,origins,comorbidities,b

  #DOA,DOD
  x=str(margins['doadod'][0]);w=str(margins['doadod'][1]); #for new
  cmd='pdftotext -x '+x+'  -W '+w+' -y 0 -H 1000  -nopgbrk -layout -f '+start_page+' -l '+end_page+' '+bulletin+' tmp.txt';os.system(cmd);

  b=[i.lower().replace('hospital','').replace('at ','') for i in open('tmp.txt').readlines()]
  b=[i for i in b if i.strip() and not ('page' in i and 'of' in i)]
  borig=copy.copy(b)
  if 'place' not in margins: #check and correct for mixup of DOD and place in some bulletins
    for j in range(len(b)):
      i=b[j];last_term0=''
      if 'designa' in i or 'private' in i:
        lindex=1
        # ~ i=i.lower().replace('at private','private').replace('at designated','designated')
        # ~ b[j]=b[j].lower().replace('at private','private').replace('at designated','designated')
        #clear out string, swap with above column
        start_char_idx=''
        if 'desig' in i: start_char_idx=b[j].index('desig')
        else:
          # ~ print 'beofre getting start_char_idx, b[j]: '+str(b[j])
          start_char_idx=b[j].index('priva')
        sub_index=3
        last_term=b[j-1][start_char_idx-sub_index:].strip()
        if last_term.count('-')<2 or (not last_term.strip()[0].isdigit()):
          sub_index+=3
          last_term0=borig[j-1][start_char_idx-sub_index:].strip()
          
          
        if (not last_term) or (last_term.strip()=='at'): #sometimesblank
          lindex+=1
          if (last_term.strip()=='at'): b[j-1]=b[j-1].replace('at','')
          
          last_term=b[j-2].strip()
            
          if last_term in ['at']:
            lindex+=1
            last_term=b[j-3].strip()
            
        last_term=last_term.replace('.','-').replace('/','-')
        if stop_debug=='doadod1':
          print(('backtrack to -'+str(lindex)+' in '+i.strip()+' last_term: '+last_term)); #+' ,start_char_idx: '+str(start_char_idx)
          # ~ if last_term0:  print 'skipping setting last_erm to'+highlight(last_term0)
              
        if not last_term[0].isdigit() and last_term.count('-')>0:
          # ~ print 'in last_term: '+last_term+' first elem was not digit, but has -'
          #assign to current date as hack
          date_init=bulletin.split('_')[0].strip()
          last_term=date_init+last_term
        if last_term[0].isdigit() and last_term.count('-')==2: #means it is date
          # ~ start_char_idx=b[j].index('desig')
          # ~ last_date=b[j-1][start_char_idx-5:]
          # ~ b[j]=b[j].replace('designated',' '*len('designated')).replace('private',' '*len('private'))
          b[j-lindex]='  '
          b[j]=b[j].lower().replace('at designated',' ').replace('at private','').replace('designated','').replace('private','')
          if lindex==1:
            b[j]+='  '+last_term.replace('at','').strip()
            b[j]=b[j].replace('\n','').replace('_','').strip()
            if stop_debug=='doadod1': print(('\tcorrected to: '+highlight(b[j])))
          else:
            b[j-1]+='  '+last_term.replace('at','').strip()
            b[j-1]=b[j-1].replace('\n','').replace('_','').strip()
            if stop_debug=='doadod1': print(('\tcorrected to: '+highlight(b[j-1])))
            
  
  b=[i.replace('.','-').replace('/','-') for i in b]; #correct for malformed bulletins
  b=[i.strip() for i in b if i.strip() and (i.strip()[0].isdigit() and i.count('-')>1 ) or ('rought' in i and i.count('-')>1 ) ]
  if bulletin=='08_24_2020.pdf':#workarounds for malformed bulletin
    b.insert(95,'19-08-2020')
    b[15]='13-08-2020 '+b[15]
  elif bulletin=='07_23_2020.pdf':#workarounds for malformed bulletin
    b.insert(49,'15-07-2020')
  elif bulletin=='07_28_2020.pdf':#workarounds for malformed bulletin
    b.insert(47,'23-07-2020 23-07-2020')
    
  if stop_debug=='doadod1': #prelim
    print('stopping at beginning of doadod proc')
    return districts,patient_numbers,ages,genders,origins,comorbidities,b

  
    
  dates_of_admission=[];dates_of_death=[]
  for i in b:
    #correct for malformed bulletins
    i=i.replace('-202020','-2020').replace('-20020','-2020').replace('-2020s','-2020').replace('at','').strip(); 
    i=i.replace('-072020','-07-2020').replace('-082020','-08-2020').replace('-092020','-09-2020').replace('-2002','-2020')
    i=i.replace('23- 08-2020','23-08-2020')
    
    if 'rought' in i:
      if stop_debug=='doadod':
        print(('parsing single line "rought" string in '+i))
      date_of_admission=datetime_doa_marker
      ll=i.split()[-1].strip()
      date_of_death=datetime.datetime.strptime(ll,'%d-%m-%Y')
    else:
      l=i.split()
      
      if len(l)==1: #brought dead on date
        date_of_admission=datetime_doa_marker; #use 1 jan as marker
        ll=l[0].replace('at','').strip()
        if '-2020' not in ll:
          if '-200' in ll: ll=ll[:-1]+'20'
          elif '-20' in ll:ll+='20'
          elif ll.endswith('-'):ll+='2020'
        date_of_death=datetime.datetime.strptime(ll,'%d-%m-%Y')
      else:
        ll=l[0].replace('at','').strip()
        if '-2020' not in ll:
          if '-200' in ll: ll=ll[:-1]+'20'
          elif '-202' in ll:ll+='0'
          elif '-20' in ll:ll+='20'
          elif ll.endswith('-'):ll+='2020'
        try:
          date_of_admission=datetime.datetime.strptime(ll,'%d-%m-%Y')
        except ValueError:
          print(('got unusual date string: %s when converting to date_of_admission, i: %s' %(ll,i)))
          date_of_admission=datetime_doa_marker
        ll=l[1].replace('at','').strip()
        if '-2020' not in ll:
          if '-200' in ll: ll=ll[:-1]+'20'
          elif '-20' in ll:ll+='20'
          elif ll.endswith('-'):ll+='2020'
        try:
          date_of_death=datetime.datetime.strptime(ll,'%d-%m-%Y')
        except ValueError:
          print(('got unusual date string: %s when converting to date_of_death, i: %s' %(ll,i)))
          date_of_death=datetime_doa_marker
    dates_of_admission.append(date_of_admission)
    dates_of_death.append(date_of_death)

  if stop_debug=='doadod': #prelim
    print('stopping at end of doadod proc')
    return districts,patient_numbers,ages,genders,origins,comorbidities,dates_of_admission,dates_of_death,b

  # ~ cmd='pdftotextx -marginl 500 -marginr 20 -margint 10 -marginb 40 -nopgbrk -layout -table -f '+start_page+' -l '+end_page+' '+bulletin+' tmp.txt';os.system(cmd);
  # ~ b=[i.strip() for i in open('tmp.txt').readlines() if i.strip() if ('private' in i.strip().lower() or 'designated' in i.strip().lower())]

  # ~ hospital_types=[]
  # ~ for i in b:    hospital_types.append(i.lower())

  fatalities=[]

  for j in range(len(districts)):

    try:
      district=districts[j]
  
      patient_number=patient_numbers[j]
      age=ages[j]
      gender=genders[j]
      origin=origins[j]
      comorbidity=comorbidities[j]
      
      date_of_admission=dates_of_admission[j]
      date_of_death=dates_of_death[j]
      # ~ hospital_type=hospital_types[j]
    except IndexError: #some index was incomplete
      print('---')
      print(('districts',len(districts)))
      print(('patient_numbers',len(patient_numbers)))
      print(('ages',len(ages)))
      print(('genders',len(genders)))
      print(('origins',len(origins)))
      print(('comorbidities',len(comorbidities)))
      print(('dates_of_admission',len(dates_of_admission)))
      print(('dates_of_death',len(dates_of_death)))
      # ~ print 'hospital_types',len(hospital_types)
      continue

    fatality=generic_fatality(district,patient_number,age,gender,origin,comorbidity,date_of_admission,date_of_death,bulletin_date)
    fatalities.append(fatality)
      
  return fatalities
      
  
def karnataka_parse_deaths_restricted(bulletin='09_09_2020.pdf',bulletin_date=datetime.datetime(2020, 9, 9, 0, 0),page_range='',stop_debug=''):
  # ~ if stop_debug and (not page_range): #means coming from debug
  if (not page_range): #means coming from debug
    (bulletin_date,annex_range)=karnataka_bulletin_parser(bulletin,return_date_only=True)
    page_range=annex_range['deaths']
    
  start_page=str(page_range[0])
  end_page=str(page_range[1])

  margins=karnataka_bulletin_get_margins(bulletin,page_range)
  if not margins and stop_debug:
    print(('no margins found with page_range: '+str(page_range)))

  format_type=1;#means place column exists
  if 'place' not in margins: format_type=0;#place colum does not exist

  #get districts name
  # ~ districts=[]
  # ~ x=str(margins['district'][0]);w=str(margins['district'][1]); #for new
  # ~ cmd='pdftotext -x '+x+'  -W '+w+' -y 0 -H 1000  -nopgbrk -layout -f '+start_page+' -l '+end_page+' '+bulletin+' tmp.txt';os.system(cmd);
  # ~ b=[i.strip() for i in open('tmp.txt').readlines() if i.strip().lower().startswith(tuple(karnataka_districts_map.keys()))]

  # ~ districts=[helper_map_district_start_char_to_fullname(i) for i in b]

  # ~ if stop_debug=='district':
    # ~ print('stopping after getting district info')
    # ~ return districts,b

  #p.no,gender,age,origin
  x=str(margins['spnotodesc'][0]);w=str(margins['spnotodesc'][1]); #for new
  cmd='pdftotext -x '+x+'  -W '+w+' -y 0 -H 1000  -nopgbrk -layout -f '+start_page+' -l '+end_page+' '+bulletin+' tmp.txt';os.system(cmd);
  b0=[i.strip() for i in open('tmp.txt').readlines() if i.strip()]
  b=[i.strip() for i in b0 if i.strip()[0].isdigit()]
  b=[i for i in b if len(i)>6];#check for minimum length

  patient_numbers=[];ages=[];genders=[];origins=[];idx=-1
  for i in b:
    idx+=1
    if len(i.split())<4:      
      #HACK for error for "contact of P-18548" etc
      last_entry=b0[b0.index(i)-1]
      if stop_debug=='origin':
        print(('when parsing origin, field in b was less than 4 for: '+i+' last_entr: '+last_entry))
        
      if last_entry.lower().startswith(('contact','ct of','asymp','under','sari','ili','e from')):
        patient_number=i.split()[0];age=i.split()[1];gender=i.split()[2]
        if last_entry.lower().startswith(('contact','ct of','e from')): origin='CONT'
        elif last_entry.lower().startswith('asymp'): origin='ASYM'
        elif last_entry.lower().startswith('under'): origin='UNKN'
        elif last_entry.lower().startswith('sari'): origin='SARI'
        elif last_entry.lower().startswith('ILI'): origin='ILI'
        if age.lower().startswith(('mont','mo','3m')):age='1'
        patient_numbers.append(patient_number);ages.append(age);genders.append(gender);origins.append(origin)
      
      elif last_entry.lower().startswith('mo'):#age is in months
        patient_number=i.split()[0];gender=i.split()[1]
        origin=i.split()[2];age='1'
        patient_numbers.append(patient_number);ages.append(age);genders.append(gender);origins.append(origin)
      elif last_entry.lower().startswith(('mal','fem','ma')):#malformed gender data
        patient_number=i.split()[0];age=i.split()[1]
        origin=i.split()[2];
        if last_entry.lower().startswith('ma'): gender='M'
        elif last_entry.lower().startswith('fem'): gender='F'
        patient_numbers.append(patient_number);ages.append(age);genders.append(gender);origins.append(origin)
      
      continue; #need all fields
    patient_number=i.split()[0];age=i.split()[1]
    gender=i.split()[2];origin=i.split()[3]
    if 'under' in origin or 'contact' in origin or 'trac' in origin: origin='CONT'
    if age.lower().startswith(('mont','mo','3m')):age='1'
    patient_numbers.append(patient_number);ages.append(age);genders.append(gender);origins.append(origin)

  if stop_debug=='origin':
    print('stopping after getting origin info')
    # ~ return districts,patient_numbers,ages,genders,origins,b
    return patient_numbers,ages,genders,origins,b
    


  #DOA,DOD
  x=str(margins['doadod'][0]);w=str(margins['doadod'][1]); #for new
  cmd='pdftotext -x '+x+'  -W '+w+' -y 0 -H 1000  -nopgbrk -layout -f '+start_page+' -l '+end_page+' '+bulletin+' tmp.txt';os.system(cmd);

  b=[i.lower().replace('hospital','').replace('at ','') for i in open('tmp.txt').readlines()]
  b=[i.strip() for i in b if i.strip() and not ('page' in i and 'of' in i) and i.strip()[0].isnumeric() and ('-' in i or '/' in i) ]
  b=[i.replace('-21','-2021').replace('26/4/21','26-04-2021').replace('25/4/21','25-04-2021').replace('4/18/','18-04-').replace('4/16/','16-04-').replace('4/19/','19-04-').replace('4/17/','17-04-').replace('4/20/','20-04-').replace('4/28/','28-04-').replace('4/21/','21-04-').replace('4/22/','22-04-').replace('4/24/','24-04-').replace('4/23/','23-04-').replace('4/25/','25-04-').replace('4/26/','26-04-').replace('4/27/','27-04-').replace('4/28/','28-04-').replace('4/30/','30-04-').replace('27/04/21','27-04-2021').replace('gàazàä','').replace('ªàägàtzà','').replace('¸àéuàèºàzà°','').replace('-20221','-2021').replace('-201','-2021') for i in b];#correct common errors
  # ~ doubles=[i.split() for i in b if len(i.split())>1]
  # ~ singles=[i.split() for i in b if len(i.split())==1]
   
  dates_of_admission=[];dates_of_death=[]
  for i in b:
    if '/2021' in i: i=i.replace('/','-');  #print(i)
    elif '.2021' in i: i=i.replace('.','-');  #print(i)
    i=i.split()
    
    if len(i)==3:
      if i[1]=='021': i[0]+='021';i.pop(1)
    if len(i)==1:
      try:
        doa=datetime.datetime.strptime(i[0],'%d-%m-%Y')
      except:
        print('error converting doa '+i[0]+' : '+i)
        return
      dates_of_admission.append(doa);dates_of_death.append(doa)
    else:
      try:
        doa=datetime.datetime.strptime(i[0],'%d-%m-%Y')
      except:
        print('error converting doa '+i[0]+' '+str(i))
        return
      try:
        dod=datetime.datetime.strptime(i[1].replace('.','-'),'%d-%m-%Y')
      except:
        print('error converting dod '+i[1])
        return
      dates_of_admission.append(doa);dates_of_death.append(dod)
   #HACK
  if bulletin=='04_10_2021.pdf':
    dates_of_admission.insert(13,datetime.datetime(2021, 4,5,0,0))
    dates_of_death.insert(13,datetime.datetime(2021, 4,5,0,0))

  if stop_debug=='doadod': #prelim
    print('stopping at end of doadod proc')
    # ~ return districts,patient_numbers,ages,genders,origins,dates_of_admission,dates_of_death,b
    return patient_numbers,ages,genders,origins,dates_of_admission,dates_of_death,b

  # ~ cmd='pdftotextx -marginl 500 -marginr 20 -margint 10 -marginb 40 -nopgbrk -layout -table -f '+start_page+' -l '+end_page+' '+bulletin+' tmp.txt';os.system(cmd);
  # ~ b=[i.strip() for i in open('tmp.txt').readlines() if i.strip() if ('private' in i.strip().lower() or 'designated' in i.strip().lower())]

  # ~ hospital_types=[]
  # ~ for i in b:    hospital_types.append(i.lower())

  fatalities=[]

  for j in range(len(ages)):

    try:
      # ~ district=districts[j]
      district=''
  
      patient_number=patient_numbers[j]
      age=ages[j]
      gender=genders[j]
      origin=origins[j]
      # ~ comorbidity=comorbidities[j]
      comorbidity=''
      
      date_of_admission=dates_of_admission[j]
      date_of_death=dates_of_death[j]
      # ~ hospital_type=hospital_types[j]
    except IndexError: #some index was incomplete
      print('---')
      # ~ print(('districts',len(districts)))
      print(('patient_numbers',len(patient_numbers)))
      print(('ages',len(ages)))
      print(('genders',len(genders)))
      print(('origins',len(origins)))
      # ~ print(('comorbidities',len(comorbidities)))
      print(('dates_of_admission',len(dates_of_admission)))
      print(('dates_of_death',len(dates_of_death)))
      # ~ print 'hospital_types',len(hospital_types)
      continue

    fatality=generic_fatality(district,patient_number,age,gender,origin,comorbidity,date_of_admission,date_of_death,bulletin_date)
    fatalities.append(fatality)
      
  return fatalities
      
  
  
def karnataka_parse_icu_usage(bulletin_date=datetime.datetime(2020, 9, 9, 0, 0),dump_only=True):
  b=[i.strip() for i in open('tmp.txt').readlines() if i.strip() and i.strip().split()[0].isdigit()]
  all_icu_obj=[];tot=0
  a=open('allicu.txt','a')
  bd=bulletin_date.strftime('%d-%m-%Y')
  a.write('##BULLETIN_DATE '+bd+'\n')
  
  for i in b:
    icu_usage=''
    for j in range(1,len(i.split())): #break at first non-digit in split[1:]
      if i.split()[j].strip().replace('(','').replace(')','').isdigit():
        icu_usage=i.split()[j].strip().replace('(','').replace(')','')        
        # ~ print 'found icu_usage: %s for line: %s' %(icu_usage,i)
        break
      j+=1
    
    
    if not icu_usage: #no "split" entry was digit
      print(('error in getting icu usage with line: %s and bulletin_date ' %(i)+str(bulletin_date)))
    
    assert(icu_usage.isdigit())
    icu_usage=int(icu_usage)
    tot+=icu_usage
    district_name=''.join(i.split()[1:j])
    
    icu_obj=generic_icu_usage(bulletin_date,district_name,icu_usage,state='Karnataka')
    a.write(district_name+' : '+str(icu_usage)+'\n')
    all_icu_obj.append(icu_obj)
  
  icu_obj=generic_icu_usage(bulletin_date,'Total',tot,state='Karnataka')
  all_icu_obj.append(icu_obj)
  a.write('Total : '+str(tot)+'\n')
  # ~ a.write('------\n')
  # ~ for i in b: a.write(i+'\n')  
  a.close()
  return all_icu_obj

  
def karnataka_parse_discharges(bulletin_date=datetime.datetime(2020, 9, 9, 0, 0),page_range=(),debug=False):
  bulletin=bulletin_date.strftime('%m_%d_%Y')+'.pdf'
  if debug and not page_range:
    (bulletin_date,annex_range)=karnataka_bulletin_parser(bulletin,return_date_only=True)
    page_range=annex_range['discharges']
    
  cmd='pdftotextx -nopgbrk -layout -table -f '+str(page_range[0])+' -l '+str(page_range[1])+' '+bulletin+' tmp.txt';os.system(cmd);
  skip_start_terms=('Total','*','Date')
  b=[i for i in open('tmp.txt').readlines() if i.strip() and not i.strip().startswith(skip_start_terms)]

  district_indices=[b.index(i) for i in b if i[0].isdigit()]
  b0=b[:]
  b=b[district_indices[0]:]; #remove header

  district_names=[];
  all_dischages_objects=[]
  
  for j in range(len(district_indices)):
    district_index=district_indices[j]
    first_line=b0[district_index].strip().replace('&',' ')
    district_name=''
    l=first_line.split()[1:]
    discharges=[]
    #parse first line
    for i in l:
      # ~ print i
      if i.isdigit():
        discharges=l[l.index(i)+1:]
        break
      else:
        district_name+=i
    #parse rest of discharges lines for district
    if j==(len(district_indices)-1): next_index=len(district_indices)-1
    else: next_index=district_indices[j+1]
    l=b0[district_index+1:next_index]
    for i in l:
      discharges.extend(i.strip().replace('&',' ').split())
      
    district_names.append(district_name)
    for patient_number in discharges:
      patient_number=patient_number.replace('n','').replace('P-','').replace(',','').strip()
      if not patient_number.isdigit(): continue #p.no must be digit
      dd=karnataka_discharge(district_name,patient_number,bulletin_date)
      if dd.district!='ERROR':      all_dischages_objects.append(dd)

  return all_dischages_objects
        
def karnataka_parse_confirmed(bulletin='07_01_2020.pdf',bulletin_date='',annex_range='',parse_txt=False):
  if not (bulletin_date and annex_range):
    bulletin_date,annex_range=karnataka_get_annexure_range(bulletin)
  if 'confirmed' not in annex_range: return #bulletin is truncated
  page_range=annex_range['confirmed']
  if parse_txt:
    b=[i for i in open('confirmed.txt') if i.strip()]
  else:
    karnataka_bulletin_get_margins_confirmed(bulletin=bulletin,page_range=page_range,execute=True)
    b=[i for i in open('tmp.txt') if i.strip()]

  indices=[i for i in range(len(b)) if b[i].strip() and b[i].split()[0].strip().isdigit() and len(b[i].split())>=4]
  special=[('bangalore rural','bengaluru'),('bangalore urban','bengaluru'),('bengaluru rural','bengaluru'),('bengaluru urban','bengaluru'),('dakshina kannada','dakshinakannada'),('uttara kannada','uttarakannada')]

  a=open('debug.txt','w');a.write('##BULLETIN_DATE '+bulletin_date.strftime('%d-%m-%Y')+'\n')
  for index in indices:
    line=b[index].strip().lower()
    for j in special: line=line.replace(j[0],j[1]); #get districts in one word
    ls=line.split()
    if len(ls)<3: #doesn't have all entries
      print(('error parsing line '+line+' in bulletin: '+bulletin))
      return
    gi=''
    if 'female' in ls: gi=ls.index('female')
    elif 'male' in ls: gi=ls.index('male')
    gender=ls[gi]
    age=ls[gi-1];sub1=False
    if len(age)>2: #age should normally be 2 go above below
      age=''   
      char_idx=b[index].lower().index('male')
      above=b[index-1][:char_idx-2];below=b[index+1][:char_idx-2];
      if above.strip() and above.strip().split()[-1].isdigit(): #age was above
        age=above.strip().split()[-1];sub1=True
      if not age and below.strip() and below.strip().split()[-1].isdigit(): #age was above
        age=below.strip().split()[-1];sub1=True
    if sub1:
      pno=ls[gi-1].replace('p-','').replace('-','').strip()
    else:
      pno=ls[gi-2].replace('p-','').replace('-','').strip()

    try:
      district=ls[gi+1]
    except:
      print(('error parsing district in line: %s in bulletin: %s' %(line,bulletin)))
      return

    #maybe it is next
    history=''
    if len(ls)>(gi+2):
      history=''.join(ls[gi+2:])
      # ~ print 'fioio'
    else: #look above and below
      char_idx=b[index].lower().index('male')+4
      above=b[index-1][char_idx:];below=b[index+1][char_idx:];
      # ~ print 'aboeve,below in history '+str(above)+' :: '+str(below)
      if above.strip(): #age was above
        history=''.join(above.lower().strip().split())
      if not history and below.strip():#history was above
        history=''.join(below.lower().strip().split())
        
    if not age.isdigit():
      print(('error parsing age: %s in line: %s in bulletin: %s' %(age,line,bulletin)))
      return
    if not pno.isdigit():
      print(('error parsing pno: %s in line: %s in bulletin: %s' %(pno,line,bulletin)))
      return
    if not history:
      print(('error parsing history in line: %s in bulletin: %s' %(line,bulletin)))
      return
    info='%s : %s : %s : %s' %(pno,age,gender,district)
    if history: info+=' : %s' %(history)
    a.write(info+'\n')
  a.close()
    
  
def karnataka_get_annexure_range(bulletin=''):
  cmd='pdftotext -layout "'+bulletin+'" tmp.txt';os.system(cmd);
  b=[i for i in open('tmp.txt').readlines() if i.strip()]  
  for i in b:
    i=i.lower().strip()
    if i.startswith(('date:','dated:')):
      date_string=i.split(':')[1].strip().replace('202020','2020').replace('/','-')
      if '-' in date_string:
        bulletin_date=datetime.datetime.strptime(date_string,'%d-%m-%Y')      
      break
  annexures=[i for i in b if 'nnexure' in i]
  annexures_indices=[b.index(i) for i in annexures]

  discharge_annex_range=[];deaths_annex_range=[];icu_annex_range=[];
  annex_range=[];lastpage=0

  #HACKS FOR MISFORMED BULLETINS
  misformed_bulletins=['08_05_2020.pdf','08_07_2020.pdf','07_18_2020.pdf']
      
  # ~ if bulletin not in misformed_bulletins:
  pagenum=1;
  for j in range(len(b)):
    i=b[j].strip();info_string='' 
    if '\x0c' in b[j]: pagenum+=1
    
    if j in annexures_indices: info_string=b[j+1].strip().lower()
    # ~ print 'info_str: '+info_str
    if 'discharge' in info_string:
      annex_range.append(('discharges',pagenum))
    elif 'death' in info_string:
      annex_range.append(('deaths',pagenum))
    elif 'icu' in info_string:
      annex_range.append(('icu',pagenum))
    elif i.endswith('2') and (j in annexures_indices):
      annex_range.append(('confirmed',pagenum))
  # ~ else:
    # ~ if bulletin=='08_05_2020.pdf': annex_range=[('discharges',5,16),('deaths',17,22),('icu',23,23)]
    # ~ elif bulletin=='08_07_2020.pdf': annex_range=[('discharges',5,16),('deaths',17,21),('icu',22,22)]    

  # ~ print annex_range
  #convert to dict
  dc={}
  for i in range(len(annex_range)):
    if i<(len(annex_range)-1):
      dc[annex_range[i][0]]=(annex_range[i][1],annex_range[i+1][1]-1)
    else:
      dc[annex_range[i][0]]=(annex_range[i][1],annex_range[i][1]+2)
  annex_range=dc
  if bulletin=='07_18_2020.pdf': annex_range={'discharges':(4,5),'deaths':(311,314),'icu':(315,315)}
  return (bulletin_date,annex_range)


def karnataka_bulletin_parser(bulletin='',return_date_only=False,return_specific=''):
  if not os.path.exists(bulletin):
    print(('%s does not exist. Please give pdf bulletin file as input' %(bulletin)))
    return -1
  cmd='pdftotext -nopgbrk -layout "'+bulletin+'" tmp.txt';os.system(cmd);
  b=[i.strip() for i in open('tmp.txt').readlines() if i.strip()]

  #find date of bulletin
  date_string='';bulletin_date=''
  for i in b:
    i=i.lower()
    if i.startswith(('date:','dated:')):
      date_string=i.split(':')[1].strip().replace('202020','2020')
      if '-' in date_string:
        bulletin_date=datetime.datetime.strptime(date_string,'%d-%m-%Y')
      elif '/' in date_string:
        bulletin_date=datetime.datetime.strptime(date_string,'%d/%m/%Y')
      break
  if bulletin=='04_18_2021_Kannada.pdf':
    bulletin_date=datetime.datetime(2021,4,18,0,0)
    
  # ~ if return_date_only:    return bulletin_date

  #find pages for Annexure 1(discharges),2(deaths),3(icu_usage)
  annexures=[i for i in b if 'nnexure' in i]
  annexures_indices=[b.index(i) for i in annexures]

  discharge_annex_range=[];deaths_annex_range=[];icu_annex_range=[];
  annex_range=[];lastpage=0

  #HACKS FOR MISFORMED BULLETINS
  misformed_bulletins=['08_05_2020.pdf','08_07_2020.pdf','07_18_2020.pdf','04_18_2021_Kannada.pdf']
      
  if bulletin not in misformed_bulletins:
    for annexure_index in annexures_indices:
      pagenum=0;info_str_set=False;info_string=''
      if annexure_index==123 and bulletin=='07_14_2020.pdf':
        annexure_index+=2
        info_string='Today\'s Discharges'.lower()
        info_str_set=True
      
      page_string=b[annexure_index-1].lower()
      if 'page' not in page_string and 'page' in b[annexure_index-2].lower():
        page_string=b[annexure_index-2].lower()
        page_string=page_string[page_string.index('page'):]
        # ~ print 'found page_num on backtrack as '+page_string
      if 'page' in page_string:
        pagenum=page_string.split('page')[1].strip().split('of')[0].strip()
        assert(pagenum.isdigit());
        pagenum=int(pagenum)+1
      else:
        if bulletin=='06_07_2020.pdf': pagenum=15
        elif bulletin=='06_07_2020.pdf': pagenum=15
        print(('"page n/n" info not found for %s with page_string: %s' %(b[annexure_index],page_string)))

      if not info_str_set:
        info_string=b[annexure_index+1].lower()
      # ~ print 'info_str: '+info_str
      if 'discharge' in info_string:
        annex_range.append(('discharges',pagenum))
      elif 'death' in info_string:
        annex_range.append(('deaths',pagenum))
      elif 'icu' in info_string:
        annex_range.append(('icu',pagenum))
  else:
    if bulletin=='08_05_2020.pdf': annex_range=[('discharges',5,16),('deaths',17,22),('icu',23,23)]
    elif bulletin=='08_07_2020.pdf': annex_range=[('discharges',5,16),('deaths',17,21),('icu',22,22)]    
    elif bulletin=='04_18_2021_Kannada.pdf': annex_range=[('discharges',6,14),('deaths',15,18),('icu',19,19)]    
  # ~ print(annex_range)
  #convert to dict
  dc={}
  for i in range(len(annex_range)):
    if i<(len(annex_range)-1):
      dc[annex_range[i][0]]=(annex_range[i][1],annex_range[i+1][1]-1)
    else:
      if bulletin_date>=datetime.datetime(2021, 4, 30, 0, 0):
        dc[annex_range[i][0]]=(annex_range[i][1],annex_range[i][1]+20)
      else:
        dc[annex_range[i][0]]=(annex_range[i][1],annex_range[i][1]+2)
  annex_range=dc
  if bulletin=='07_18_2020.pdf': annex_range={'discharges':(4,5),'deaths':(311,314),'icu':(315,315)}
  if return_date_only:    return (bulletin_date,annex_range)

  discharges='';deaths='';icu_usage=''
  #get discharges info  
  if (not return_specific) or (return_specific and return_specific=='discharges'):
    discharges=karnataka_parse_discharges(bulletin_date,annex_range['discharges'])

  #get icu info
  if (not return_specific) or (return_specific and return_specific=='icu'):
    cmd='pdftotextx -nopgbrk -layout -table -f '+str(annex_range['icu'][0])+' -l '+str(annex_range['icu'][1])+' '+bulletin+' tmp.txt';os.system(cmd);
    icu_usage=karnataka_parse_icu_usage(bulletin_date)
  
  #get deaths info
  if (not return_specific) or (return_specific and return_specific=='deaths'):
    # ~ deaths=karnataka_parse_deaths(bulletin,bulletin_date,annex_range['deaths'])
    deaths=karnataka_parse_deaths_restricted(bulletin,bulletin_date,annex_range['deaths'])

 
  
  if return_specific:
    if return_specific=='icu':
      return icu_usage
    elif return_specific=='deaths':
      return deaths
  else:
    return (discharges,icu_usage,deaths)

def karnataka_parse_icu_clipping():
  infile='allicu.txt'
  if not os.path.exists(infile) and os.path.exists('parsed_text_clippings/Karnataka_icu_details_parsed.txt'):
    infile='parsed_text_clippings/Karnataka_icu_details_parsed.txt'
  b=[i.strip() for i in open(infile).readlines() if i.strip()]
  indices=[j for j in range(len(b)) if b[j].startswith('##BULLETIN_DATE')];bulletin_date_string=''

  all_icu=[]
  bulletin_date_string=''
  for j in range(len(indices)-1):
    bulletin_date_string=b[indices[j]].split()[1]    
    bulletin_date=datetime.datetime.strptime(bulletin_date_string,'%d-%m-%Y')
    chunk=b[indices[j]+1:indices[j+1]]
    for entry in chunk:
      district=entry.split(':')[0].strip()
      try:
        icu=entry.split(':')[1].strip();
      except:
        print(('crashed in '+entry))
        return
      icu=int(icu);
      icu_obj=generic_icu_usage(bulletin_date,district,icu,state='Karnataka');all_icu.append(icu_obj)
  #last
  chunk=b[indices[-1]+1:]
  bulletin_date_string=b[indices[-1]].split()[1]    
  bulletin_date=datetime.datetime.strptime(bulletin_date_string,'%d-%m-%Y')
  for entry in chunk:
    district=entry.split(':')[0].strip()
    try:
      icu=entry.split(':')[1].strip();icu=int(icu);
    except:
      print(('crashed in '+entry))
      return
    icu_obj=generic_icu_usage(bulletin_date,district,icu,state='Karnataka');all_icu.append(icu_obj)
  all_icu.sort(key=lambda ii: ii.date)
  return all_icu

def karnataka_parser(return_specific=''):
  bulletin_pdfs=[i for i in os.listdir('.') if i.endswith('.pdf')]
  bulletin_pdfs.sort()
  all_discharges=[];all_icu_usage=[];all_deaths=[]
  if return_specific=='icu': #directly parse txt clipping of icu usage
    all_icu_usage=karnataka_parse_icu_clipping()
  for bulletin_pdf in bulletin_pdfs:
    print(('parsing bulletin %s' %(bulletin_pdf)))    
    try:
      if return_specific:
        pass
      else:
        (discharges,icu_usage,deaths)=karnataka_bulletin_parser(bulletin_pdf)
        all_discharges.extend(discharges)
        all_icu_usage.extend(icu_usage)
        all_deaths.extend(deaths)
    except:
      print(('parsing failed for :%s' %(bulletin_pdf)))
  if return_specific:
    if return_specific=='icu': return all_icu_usage
  else:    
    return (all_discharges,all_icu_usage,all_deaths)
  
# ~ Returns percent of antigen tests as fraction of daily tests in state
# as of sep 5, data on antigen tests is available for (state_name: number_of_days_of_data_available)
# ~ {u'Chhattisgarh': 16,
 # ~ u'Delhi': 68,
 # ~ u'Karnataka': 43,
 # ~ u'Kerala': 16,
 # ~ u'Ladakh': 5,
 # ~ u'Manipur': 13,
 # ~ u'Mizoram': 16,
 # ~ u'Nagaland': 13,
 # ~ u'Sikkim': 13}
def get_antigen_tests(state='Karnataka',verbose=False,do_moving_average=False):
  if len(state)==2 and state in state_code_to_name: x=state;state=state_code_to_name[state];
  x=json.load(open('state_test_data.json'))
  x=[i for i in x['states_tested_data'] if 'ratrapidantigentest' in i and i['ratrapidantigentest'] and i['state']==state]

  antigen_on_day=0;tests_on_day=0;percent_antigen=0
  all_antigen=[]
  
  for idx in range(1,len(x)):
    i=x[idx]
    date=i['updatedon']
    datetime_i=datetime.datetime.strptime(i['updatedon'],'%d/%m/%Y')
    
    tests_on_day=int(i['totaltested'])-int(x[idx-1]['totaltested'])
    antigen_on_day=int(i['ratrapidantigentest'])-int(x[idx-1]['ratrapidantigentest'])
    percent_antigen=100*(float(antigen_on_day)/tests_on_day)
    date=datetime.datetime.strptime(date,'%d/%m/%Y')
    all_antigen.append((date,tests_on_day,antigen_on_day,percent_antigen))
  
  if verbose:
    print(('For state: %s' %(state)))
    for i in all_antigen:
      (date,tests_on_day,antigen_on_day,percent_antigen)=i      
      print(('%s: %d tests,  %.1f percent (%d tests) were antigen' %(date,tests_on_day,percent_antigen,antigen_on_day)))
  if do_moving_average:
    dates,t,pa,ad=zip(*all_antigen)
    t=moving_average(t);pa=moving_average(pa);ad=moving_average(ad)
    all_antigen=list(zip(dates,t,pa,ad))
  return all_antigen
def get_pcr_tests(state='Punjab'):
  if len(state)==2 and state in state_code_to_name: x=state;state=state_code_to_name[state];
  r=csv.reader(open('pcr.csv'));info=[]
  for i in r: info.append(i)
  dates=info[0][1:]
  dates=[datetime.datetime.strptime(i+'/2020','%d/%m/%Y') for i in dates]
  pcr=''
  for i in info[1:]:
    st=i[0]
    if st!=state: continue
    data=np.int_(i[1:])
    pcr=np.append(data[0],np.diff(data))
  d={}
  for j in range(len(dates)): 
    date=dates[j];pcrr=pcr[j]
    d[date]=pcrr

  tot=get_tests(state)
  for i in tot:
    date,t=i
    if date in d:
      d[date]=(d[date],t)
  l=list(d.items());l.sort()
  l=[(i[0],i[1][0],i[1][1]) for i in l if type(i[1])==tuple]
  #return list(zip(dates,pcr))
  return l


def get_tests(state='Karnataka',date='',return_full_series=True,verbose=False,do_moving_average=False):
  if len(state)==2 and state in state_code_to_name: x=state;state=state_code_to_name[state];
  x=json.load(open('state_test_data.json'))
  x=[i for i in x['states_tested_data'] if i['state']==state]

  tests_on_day=0
  all_tests=[]
  
  for idx in range(1,len(x)):
    i=x[idx]
    date=i['updatedon']
    datetime_i=datetime.datetime.strptime(i['updatedon'],'%d/%m/%Y')
    if not i['totaltested']:
      tests_on_day=1
    else:
      if x[idx-1]['totaltested']:
        tests_on_day=int(i['totaltested'])-int(x[idx-1]['totaltested'])    
      else:
        tests_on_day=int(i['totaltested'])-int(x[idx-2]['totaltested'])    
    all_tests.append((datetime_i,tests_on_day))
  
  # ~ if verbose:
    # ~ print 'For state: %s' %(state)
    # ~ for i in all_antigen:
      # ~ (date,tests_on_day,antigen_on_day,percent_antigen)=i
      # ~ print '%s: %d tests,  %.1f percent (%d tests) were antigen' %(date,tests_on_day,percent_antigen,antigen_on_day)
  if do_moving_average:
    dates,tests=zip(*all_tests)
    tests=moving_average(tests)
    all_tests=list(zip(dates,tests))
  return all_tests

def get_positivity_district(state='Karnataka',district='Bengaluru Urban',plot=False,plot_days=''):
    if district=='RoK':
        cases=get_cases_district(state=state,district='Bengaluru Urban',case_type='confirmed_delta')
        tests=get_cases_district(state=state,district='Bengaluru Urban',case_type='tested_delta')
        cases0=get_cases('Karnataka',case_type='confirmed',return_full_series=True)
        c=list(np.diff([i[1] for i in cases0]))
        cases0=list(zip([i[0] for i in cases0][1:],c))

        tests0=get_tests('Karnataka')
        cases=cases[-100:];cases0=cases0[-100:]
        tests=tests[-100:];tests0=tests0[-100:]
        cases=[(i[0],i[1]-j[1]) for i,j in zip(cases0,cases)]
        tests=[(i[0],i[1]-j[1]) for i,j in zip(tests0,tests)]

    else:
        try: cases=get_cases_district(state=state,district=district,case_type='confirmed_delta')
        except: return
        tests=get_cases_district(state=state,district=district,case_type='tested_delta')

    cases=cases[-100:];tests=tests[-100:]
    dates=[i[0] for i in cases]
    c=[i[1] for i in cases];    t=[i[1] for i in tests]
    c=moving_average(c);t=moving_average(t)
    c=c[-90:];t=t[-90:];dates=dates[-90:]
    p=list(100*(np.array(c)/np.array(t)))
    if plot:
        plot2(dates,p,dates,t,label1='TPR',label2='Daily Tests',color1='green',color2='black',state=district)
#        formatter = mdates.ConciseDateFormatter(locator)
#        ax.xaxis.set_major_locator(locator)
#        ax.xaxis.set_major_formatter(formatter) 
#        color='tab:green'
#        dates=pylab.date2num(dates)
#        ax.plot_date(dates[-70:],p[-70:],color=color,label=district+' TPR (7-day MA)')
#        xlabel='dates';ylabel='TPR (7-day MA)'
#        ax.tick_params(axis='y', labelcolor=color)
#        ax.set_xlabel(xlabel,color=color);ax.set_ylabel(ylabel,color=color);
#
#        ax2=ax.twinx()
#        color='tab:blue'
#        ax2.tick_params(axis='y', labelcolor=color)
#        ax2.plot_date(dates[-70:],t[-70:],color=color,label=district+' daily tests (7-day MA)')
#        xlabel='dates';ylabel='daily tests (7-day MA)'
#        ax2.tick_params(axis='y', labelcolor=color)
#        ax2.set_xlabel(xlabel,color=color);ax2.set_ylabel(ylabel,color=color);
#
#        pylab.title(district+' TPR vs daily tests')
#        sp.tight_layout()
#
#        pylab.savefig(TMPDIR+district+' TPR vs daily tests.jpg');pylab.close()
    return dates,p,c,t


def get_positivity_national(do_moving_average=True,plot=False,plot_days=''):
  pass
  
def get_positivity(state='Karnataka',do_moving_average=True,plot=False,plot_days=''):
  if len(state)==2 and state in state_code_to_name: x=state;state=state_code_to_name[state];
  if state in ['','national','India']:
    d,cases=zip(*get_cases_national('confirmed'))
    d,tests=zip(*get_cases_national('tests'))
    if do_moving_average:
      cases=moving_average(cases[-360:]);tests=moving_average(tests[-360:])
      tpr=100*(np.array(cases)/np.array(tests))
      return list(zip(d[-360:],tpr))
  cases_cum=get_cases(state=state,case_type='confirmed',return_full_series=True,verbose=False)
  d=[i[0] for i in cases_cum][1:]
  c=numpy.diff([i[1] for i in cases_cum])
  window_size=7
  if do_moving_average:
    c=moving_average(c,window_size=window_size)
    # ~ d=d[window_size-1:]
  cases=list(zip(d,c))
  tests=get_tests(state=state)
  if do_moving_average:
    d=[i[0] for i in tests]    
    t=[i[1] for i in tests]
    try:
      t=moving_average(t,window_size=window_size)
    except:
      print(('error doing moving average for '+state))
      return
    # ~ d=d[window_size-1:]
    tests=list(zip(d,t))
  cd={}
  for i in cases:
    date,c=i;cd[date]=c
  td={}
  for i in tests:
    date,t=i;td[date]=t
  pd={}
  for date in td:
    if date in cd:
      if td[date]: pd[date]=100*float(cd[date])/td[date]
  p=list(pd.items());p.sort()
  #p=[i for i in p if i[1]<=60 and i[1]>0]
  p=[i for i in p if  i[1]>0]
  if plot:
    # ~ import pylab
    ax=pylab.axes()
    import matplotlib.dates as mdates
    locator = mdates.AutoDateLocator(minticks=3, maxticks=7)
    formatter = mdates.ConciseDateFormatter(locator)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(formatter) 

    dates=pylab.date2num([i[0] for i in p])
    p2=[i[1] for i in p]
    if plot_days:
        ax.plot_date(dates[-1*plot_days:],p2[-1*plot_days:],label=state)
    else:
        ax.plot_date(dates,p2,label=state)
    xlabel='Date';ylabel='Positivity in '+state;title=state+' TPR'
    if do_moving_average: ylabel+=' (7-day MA)'
    pylab.xlabel(xlabel);pylab.ylabel(ylabel);pylab.title(title);pylab.legend()
    pylab.savefig(TMPDIR+'/'+state+'_tpr.jpg',dpi=100);pylab.close()
  return p

def delhi_parse_json():
    #create delhi_status() class list from json file
    x=[i for i in json.load(open('state_test_data.json'))['states_tested_data'] if i['state']=='Delhi']
    x=[i for i in x if i['ratrapidantigentest'] and i['rt-pcrtestincludestruenatcbnaatcrispr'] and i['totaltested'] and i['bedsoccupiednormalisolation'] and i['totalnumbedsnormalisolation']]
    antigen0=int(x[0]['ratrapidantigentest'])
    pcr0=int(x[0]['rt-pcrtestincludestruenatcbnaatcrispr'])
    tests0=int(x[0]['totaltested'])
    dss=[]
    for i in x[1:]:
        date=datetime.datetime.strptime(i['updatedon'],'%d/%m/%Y')
        hos_cap=int(i['totalnumbedsnormalisolation'])
        hos_used=int(i['bedsoccupiednormalisolation'])
        antigen=int(i['ratrapidantigentest'])-antigen0
        pcr=int(i['rt-pcrtestincludestruenatcbnaatcrispr'])-pcr0
        tests=int(i['totaltested'])-tests0
        antigen0=int(i['ratrapidantigentest'])
        pcr0=int(i['rt-pcrtestincludestruenatcbnaatcrispr'])
        tests0=int(i['totaltested'])
        ds=delhi_status(date,hos_cap,hos_used,0,0,0,0,tests,pcr,antigen,0,0)
        dss.append(ds)
    return dss
#finds pecent on icus on all dates for which data is available for that state
#"state" must be fullname
# as of sep 5, data on icu usage is available for (state_name: number_of_days_of_data_available
# ~ {u'Delhi': 4 days,
 # ~ u'Haryana': 70 days,
 # ~ u'Karnataka': 67,
 # ~ u'Kerala': 27,
 # ~ u'Nagaland': 2,
 # ~ u'Punjab': 70,
 # ~ u'Sikkim': 2,
 # ~ u'Telangana': 55}
def get_people_in_icus(state='Telangana',verbose=False):
  if len(state)==2 and state in state_code_to_name: x=state;state=state_code_to_name[state];
  x=json.load(open('state_test_data.json'))
  all_icu_data=[i for i in x['states_tested_data'] if 'peopleonicubeds' in i and  i['peopleonicubeds'] and i['state']==state]
  if not all_icu_data:
    print(('State: %s does not have any data on ICU usage (as per covid19indiadotorg API)' %(state)))
    return 

  all_percent_icu=[]
  for entry in all_icu_data:
    icu_usage=int(entry['peopleonicubeds'])
    date_of_entry=entry['updatedon']
    actives_on_this_date=get_cases(state,date_of_entry,case_type='active')
    percent_icu=100*(float(icu_usage)/actives_on_this_date)
    all_percent_icu.append((date_of_entry,percent_icu,icu_usage))

  if verbose:
    print(('For state: %s, the variation of pecent of patients in ICU is ..' %(state)))
    for i in all_percent_icu:
      print(('%s : %.3f (%d in icu)' %(i[0],i[1],i[2])))
  return all_percent_icu

def estimate_lag():
  states=['Haryana',]
  for state in states:
    d=get_cases(state=states,case_type='deaths',return_full_series=True)

def state_demographics(state='Punjab'):
  if len(state)==2 and state in state_code_to_name: x=state;state=state_code_to_name[state];
  import csv
  
  a=open('population_pyramid_all_states.csv');r=csv.reader(a);info=[];
  for i in r: info.append(i)
  pop=[i for i in info if state.lower() in i[0].lower()][1:-3];
  totinfo=[i for i in info if (state.lower() in i[0].lower()) and ('all ages' in i[1].lower())][0];
  del info;a.close()

  state_total_pop=int(totinfo[2])
  state_total_male=int(totinfo[3])
  state_total_female=int(totinfo[4])

  gender_ratio=float(state_total_female)/state_total_male
  return (totinfo,gender_ratio,pop)
  
    
#finds pecent on ventilators on all dates for which data is available for that state
#"state" must be fullname
# as of sep 5, data on ventilators is avialable for (state_name: number_of_days_of_data_available
# ~ {u'Delhi': 7 days
 # ~ u'Gujarat': 33,
 # ~ u'Haryana': 73,
 # ~ u'Kerala': 27,
 # ~ u'Punjab': 88,
 # ~ u'Telangana': 11}
def get_people_on_ventilators(state='Telangana',verbose=False):
  if len(state)==2 and state in state_code_to_name: x=state;state=state_code_to_name[state];
  x=json.load(open('state_test_data.json'))
  all_ventilator_data=[i for i in x['states_tested_data'] if i['state']==state and i['peopleonventilator']]
  if not all_ventilator_data:
    print(('State: %s does not have any data on ventilator usage (as per covid19indiadotorg API)' %(state)))
    return 

  all_percent_ventilator=[]
  for entry in all_ventilator_data:
    ventilator_usage=int(entry['peopleonventilator'])
    date_of_entry=entry['updatedon']
    actives_on_this_date=get_cases(state,date_of_entry,case_type='active')
    percent_ventilator=100*(float(ventilator_usage)/actives_on_this_date)
    all_percent_ventilator.append((date_of_entry,percent_ventilator,ventilator_usage))

  if verbose:
    print(('For state: %s, the variation of pecent of patients on ventilator is ..' %(state)))
    for i in all_percent_ventilator:
      print(('%s : %.3f (%d on ventilator)' %(i[0],i[1],i[2])))
  return all_percent_ventilator

def analysis(state='Uttar Pradesh',extra=False,plot_days='',width_days='',doboth=True):
  if len(state)==2 and state in state_code_to_name: x=state;state=state_code_to_name[state];#print('expanded %s to %s' %(x,state))
  deaths=get_cases(state=state,case_type='deaths',return_full_series=True,verbose=False)
  deaths=[i for i in deaths if i[0]>=datetime.datetime(2020,6,1,0,0)]
  dates2=pylab.date2num([i[0] for i in deaths][1:]);d=moving_average(numpy.diff([i[1] for i in deaths]))

  deaths=get_cases(state=state,case_type='confirmed',return_full_series=True,verbose=False)
  deaths=[i for i in deaths if i[0]>=datetime.datetime(2020,6,1,0,0)]
  dates=pylab.date2num([i[0] for i in deaths][1:]);c=moving_average(numpy.diff([i[1] for i in deaths]))

  p=get_positivity(state=state)
  t=get_tests(state=state)
  dates4=pylab.date2num([i[0] for i in t]);t=moving_average([i[1] for i in t])
  dates3=pylab.date2num([i[0] for i in p]);p=[i[1] for i in p]
#  if state=='Delhi':
#    for j in range(len(p)):
#      if p[j]>15: p[j]=2
  
  if plot_days:
      c=c[-1*plot_days:]
      t=t[-1*plot_days:]
      d=d[-1*plot_days:]
      p=p[-1*plot_days:]
      dates=dates[-1*plot_days:]
      dates2=dates[-1*plot_days:]
      dates3=dates[-1*plot_days:]
      dates4=dates[-1*plot_days:]
      
      if width_days:
        c=c[:width_days];
        t=t[:width_days]
        d=d[:width_days]
        p=p[:width_days]
        dates=dates[:width_days]
        dates2=dates[:width_days]
        dates3=dates[:width_days]
        dates4=dates[:width_days]
  sp,ax=pylab.subplots()
    
  locator = mdates.AutoDateLocator(minticks=3, maxticks=7)
  # ~ formatter = mdates.ConciseDateFormatter(locator)
  formatter = mdates.ConciseDateFormatter(locator)
  ax.xaxis.set_major_locator(locator)
  ax.xaxis.set_major_formatter(formatter) 

  color = 'tab:blue'
  ax.set_xlabel('Date')
  ax.set_ylabel(state+' new daily cases (7-day MA)',color=color)
  ax.plot_date(dates,c,color=color,label=state+' new daily cases (7-day MA)')
  ax.tick_params(axis='y', labelcolor=color)
  ax.legend(loc='lower left',fontsize=5);

  ax2=ax.twinx()
  color = 'tab:red'
  ax2.xaxis.set_major_locator(locator)
  ax2.xaxis.set_major_formatter(formatter) 

  ax2.set_ylabel(state+' Daily deaths (7-day MA)',color=color)
  ax2.plot_date(dates2,d,color=color,label=state+' daily deaths (7-day MA)')
  ax2.tick_params(axis='y', labelcolor=color)
  ax2.legend(loc='lower right',fontsize=5);
  sp.tight_layout()

  title=state+' daily cases vs daily deaths'
  pylab.title(title);
  #pylab.savefig(TMPDIR+state+' daily cases vs daily deaths.jpg',dpi=150)
  pylab.savefig(TMPDIR+state+' daily cases vs daily deaths.jpg',bbox_inches='tight')
  pylab.close()
  
  sp,ax=pylab.subplots()
  locator = mdates.AutoDateLocator(minticks=3, maxticks=7)
  # ~ formatter = mdates.ConciseDateFormatter(locator)
  formatter = mdates.ConciseDateFormatter(locator)
  ax.xaxis.set_major_locator(locator)
  ax.xaxis.set_major_formatter(formatter) 

  color = 'tab:blue'
  ax.set_xlabel('Date')
  ax.set_ylabel(state+' new daily cases (7-day MA)',color=color)
  ax.plot_date(dates,c,color=color,label=state+' new daily cases (7-day MA)')
  ax.tick_params(axis='y', labelcolor=color)
  ax.legend(loc='lower left',fontsize=5);

  ax2=ax.twinx()
  locator = mdates.AutoDateLocator(minticks=3, maxticks=7)
  # ~ formatter = mdates.ConciseDateFormatter(locator)
  formatter = mdates.ConciseDateFormatter(locator)
  ax2.xaxis.set_major_locator(locator)
  ax2.xaxis.set_major_formatter(formatter) 

  color = 'tab:green'
  ax2.set_ylabel(state+' Test Positivity Rate (7-day MA)',color=color)
  ax2.plot_date(dates3,p,color=color,label=state+' TPR (7-day MA)')
  ax2.tick_params(axis='y', labelcolor=color)
  ax2.legend(loc='lower right',fontsize=5);
  sp.tight_layout()

  title=state+' daily cases vs TPR'
  pylab.title(title);  
  #pylab.savefig(TMPDIR+state+' daily cases vs TPR.jpg',dpi=150)

  pylab.savefig(TMPDIR+state+' daily cases vs TPR.jpg',bbox_inches='tight')
  pylab.close()

  if doboth:


    sp,ax=pylab.subplots()

    color = 'black'
    locator = mdates.AutoDateLocator(minticks=3, maxticks=7)
    # ~ formatter = mdates.ConciseDateFormatter(locator)
    formatter = mdates.ConciseDateFormatter(locator)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(formatter) 

    ax.set_xlabel('Date')
    ax.set_ylabel(state+' daily tests(7-day MA)',color=color)
    ax.plot_date(dates4,t,color=color,label=state+' daily tests (7-day MA)')
    ax.tick_params(axis='y', labelcolor=color)
    ax.legend(loc='lower left',fontsize=5);

    ax2=ax.twinx()
    color = 'tab:green'
    locator = mdates.AutoDateLocator(minticks=3, maxticks=7)
    # ~ formatter = mdates.ConciseDateFormatter(locator)
    formatter = mdates.ConciseDateFormatter(locator)
    ax2.xaxis.set_major_locator(locator)
    ax2.xaxis.set_major_formatter(formatter) 

    ax2.set_ylabel(state+' Test Positivity Rate (7-day MA)',color=color)
    ax2.plot_date(dates3,p,color=color,label=state+' TPR (7-day MA)')
    ax2.tick_params(axis='y', labelcolor=color)
    ax2.legend(loc='lower right',fontsize=5);
    sp.tight_layout()

    title=state+' daily tests vs TPR'
    pylab.title(title);  
    #pylab.savefig(TMPDIR+state+' daily cases vs TPR.jpg',dpi=150)

    pylab.savefig(TMPDIR+state+' daily tests vs TPR.jpg',bbox_inches='tight')
    pylab.close()
  if extra:
      yy=get_antigen_tests(state)
      ap=moving_average([i[-1] for i in yy])
      ad=[i[0] for i in yy]
      # ~ ad=[datetime.datetime.strptime(i[0],'%d/%m/%Y') for i in yy]
      ad=pylab.date2num(ad)
      if plot_days:
          ap=ap[-1*plot_days:]
          ad=ad[-1*plot_days:]
      
      sp,ax=pylab.subplots()
      locator = mdates.AutoDateLocator(minticks=3, maxticks=7)
      # ~ formatter = mdates.ConciseDateFormatter(locator)
      formatter = mdates.ConciseDateFormatter(locator)
      ax.xaxis.set_major_locator(locator)
      ax.xaxis.set_major_formatter(formatter) 

      color = 'tab:grey'
      ax.set_xlabel('Date')
      ax.set_ylabel(state+' percent rapid antigen in daily tests (7-day MA)',color=color)
      ax.plot_date(ad,ap,color=color,label=state+' percent rapid antigen (7-day MA)')
      ax.tick_params(axis='y', labelcolor=color)
      ax.legend(loc='lower left',fontsize=5);
    
      ax2=ax.twinx()
      locator = mdates.AutoDateLocator(minticks=3, maxticks=7)
      # ~ formatter = mdates.ConciseDateFormatter(locator)
      formatter = mdates.ConciseDateFormatter(locator)
      ax2.xaxis.set_major_locator(locator)
      ax2.xaxis.set_major_formatter(formatter) 

      color = 'tab:green'
      ax2.set_ylabel(state+' Test Positivity Rate (7-day MA)',color=color)
      ax2.plot_date(dates3,p,color=color,label=state+' TPR (7-day MA)')
      ax2.tick_params(axis='y', labelcolor=color)
      ax2.legend(loc='lower right',fontsize=5);
      sp.tight_layout()
    
      title=state+' percent rapid antigen tests vs TPR'
      pylab.title(title);  
      #pylab.savefig(TMPDIR+state+' daily cases vs TPR.jpg',dpi=150)

      pylab.savefig(TMPDIR+state+' percent antigen vs TPR.jpg',bbox_inches='tight')
      pylab.close()

  
def webp():
    x=[i for i in os.listdir('.') if i.endswith(('.jpg','.jpeg','.png'))];x.sort()
    from PIL import Image;import tqdm
    os.system('mkdir -p encoded')
    for i in tqdm.tqdm(x,desc='making webp'):
        y=Image.open(i)
        y.save('encoded/'+os.path.splitext(i)[0]+'.webp')
        

def analysis_undercounting_karnataka(district='Bengaluru Urban',verbose=True,plot_days=''):
  icu=karnataka_parse_icu_clipping()
  dates,ic=list(zip(*[(i.date,i.icu) for i in icu if i.district==district.replace(' ','')]))
  

  dates2,d=list(zip(*get_cases_district(state='Karnataka',district=district,case_type='deaths_delta')))
  if verbose: print(('got %s daily deaths' %(district)))
  dates3,a=list(zip(*get_cases_district(state='Karnataka',district=district,case_type='active')))

  ic=moving_average(ic);d=moving_average(d);a=moving_average(a)

  plot2(dates,ic,dates2,d,label1='ICU use in '+district,label2='Daily deaths in '+district,color2='red',state='Karnataka',plot_days=plot_days)
  plot2(dates,ic,dates3,a,label1='ICU use in '+district,label2='Active cases in '+district,color2='orange',state='Karnataka',plot_days=plot_days)

#  sp,ax=pylab.subplots()
#
#  color = 'tab:blue'
#  ax.set_xlabel('Date')
#  ax.set_ylabel(district+'ICU usage (7-day MA)',color=color)
#  ax.plot_date(pylab.date2num(dates),ic,color=color,label=district+' ICU usage (7-day MA)')
#  ax.tick_params(axis='y', labelcolor=color)
##  ax.legend(loc='upper left');
#
#  ax2=ax.twinx()
#  color = 'tab:red'
#  ax2.set_ylabel('Daily deaths (7-day MA)',color=color)
#  ax2.plot_date(pylab.date2num(dates2),d,color=color,label=district+' daily deaths (7-day MA)')
#  ax2.tick_params(axis='y', labelcolor=color)
##  ax2.legend(loc='lower right');
#  # ~ sp.tight_layout()
#
#  title=district+' ICU use vs daily deaths'
#  pylab.title(title);
#
#  
#  sp,ax=pylab.subplots()
#
#  color = 'tab:blue'
#  ax.set_xlabel('Date')
#  ax.set_ylabel(district+'ICU usage (7-day MA)',color=color)
#  ax.plot_date(pylab.date2num(dates),ic,color=color,label=district+' ICU usage (7-day MA)')
#  ax.tick_params(axis='y', labelcolor=color)
##  ax.legend(loc='upper left');
#
#  ax2=ax.twinx()
#  color = 'tab:orange'
#  ax2.set_ylabel('Active cases (7-day MA)',color=color)
#  ax2.plot_date(pylab.date2num(dates3),a,color=color,label=district+' active cases (7-day MA)')
#  ax2.tick_params(axis='y', labelcolor=color)
##  ax2.legend(loc='lower right');
#  # ~ sp.tight_layout()
#
#  title=district+' ICU use vs active cases'
#  pylab.title(title);
  
  
def analysis_undercounting(state='Haryana',atype='ventilator',plot_days=''):
  if len(state)==2 and state in state_code_to_name: x=state;state=state_code_to_name[state];#print('expanded %s to %s' %(x,state))
  if atype in ['v','ventilator','ventilators']:
    y=get_people_on_ventilators(state)
  elif atype in ['i','icu','icus']:
    y=get_people_in_icus(state)
  elif atype in ['b','beds','hospital beds']:
    y=get_beds(state)
  if atype in ['b','beds','hospital beds']:
    dates,x,b=zip(*y)
  else:
    dates=pylab.date2num([datetime.datetime.strptime(i[0],'%d/%m/%Y') for i in y]);
  v=moving_average([i[2] for i in y])


  deaths=get_cases(state=state,case_type='deaths',return_full_series=True,verbose=False)
  actives=get_cases(state=state,case_type='active',return_full_series=True,verbose=False)
  
  dates2=pylab.date2num([i[0] for i in deaths][1:]);
  d=moving_average(numpy.diff([i[1] for i in deaths]))
  dates3=pylab.date2num([i[0] for i in actives]);
  a=moving_average([i[1] for i in actives])
  
  if plot_days:
      dates=dates[-1*plot_days:]
      dates2=dates2[-1*plot_days:]
      dates3=dates3[-1*plot_days:]
      v=v[-1*plot_days:]
      d=d[-1*plot_days:]
      a=a[-1*plot_days:]

  sp,ax=pylab.subplots()

  color = 'tab:blue'
  locator = mdates.AutoDateLocator(minticks=3, maxticks=7)
  # ~ formatter = mdates.ConciseDateFormatter(locator)
  formatter = mdates.ConciseDateFormatter(locator)
  ax.xaxis.set_major_locator(locator)
  ax.xaxis.set_major_formatter(formatter) 

  ax.set_xlabel('Date')
  ax.set_ylabel(atype+' used (7-day MA)',color=color)
  ax.plot_date(dates,v,color=color,label=state+' '+atype+' patients (7-day MA)')
  ax.tick_params(axis='y', labelcolor=color)
  ax.legend(loc='lower left',fontsize=6)
  ax.legend(loc='lower left',fontsize=6)

  ax2=ax.twinx()
  color = 'tab:red'
  locator = mdates.AutoDateLocator(minticks=3, maxticks=7)
  # ~ formatter = mdates.ConciseDateFormatter(locator)
  formatter = mdates.ConciseDateFormatter(locator)
  ax2.xaxis.set_major_locator(locator)
  ax2.xaxis.set_major_formatter(formatter) 

  ax2.set_ylabel('Daily deaths (7-day MA)',color=color)
  ax2.plot_date(dates2,d,color=color,label=state+' daily deaths (7-day MA)')
  ax2.tick_params(axis='y', labelcolor=color)
  ax2.legend(loc='lower right',fontsize=6)

  title=atype+' vs daily deaths in '+state
  pylab.title(title);  
  pylab.savefig(TMPDIR+state+'_'+atype+' vs daily deaths.jpg',dpi=150)
  pylab.close()


  sp,ax=pylab.subplots()

  color = 'tab:blue'
  locator = mdates.AutoDateLocator(minticks=3, maxticks=7)
  # ~ formatter = mdates.ConciseDateFormatter(locator)
  formatter = mdates.ConciseDateFormatter(locator)
  ax.xaxis.set_major_locator(locator)
  ax.xaxis.set_major_formatter(formatter) 

  ax.set_xlabel('Date')
  ax.set_ylabel(atype+' used (7-day MA)',color=color)
  ax.plot_date(dates,v,color=color,label=state+' '+atype+' patients (7-day MA)')
  ax.tick_params(axis='y', labelcolor=color)
  ax.legend(loc='lower left',fontsize=6)

  ax2=ax.twinx()
  color = 'tab:orange'
  locator = mdates.AutoDateLocator(minticks=3, maxticks=7)
  # ~ formatter = mdates.ConciseDateFormatter(locator)
  formatter = mdates.ConciseDateFormatter(locator)
  ax2.xaxis.set_major_locator(locator)
  ax2.xaxis.set_major_formatter(formatter) 

  ax2.set_ylabel('Daily deaths (7-day MA)',color=color)
  ax2.plot_date(dates3,a,color=color,label=state+' active cases (7-day MA)')
  ax2.tick_params(axis='y', labelcolor=color)
  ax2.legend(loc='lower right',fontsize=6)

  title=atype+' vs active cases in '+state
  pylab.title(title);  
  pylab.legend(fontsize=7)
  pylab.savefig(TMPDIR+state+'_'+atype+' vs active cases.jpg',dpi=150)
  pylab.close()

def cdr_func(tpr,maxi=14,mini=10): 
  #linear function goes from mini to maxi as TPR goes from 1% to 35%
  b=(mini-maxi)/34.;a=maxi-((mini-maxi)/34);
  return a+(b*tpr)

def r0_func(date='',ro_init=3,ro_alpha=4.,r0_delta=7,time_shift=0,time_shift2=0,time_shift3=0,plot=False,return_series=False):
 # ~ if time_shift: print('got shift ',time_shift)
 if return_series:
   dates=pd.date_range('2021-02-01','2021-06-10').to_pydatetime()
   r0=[r0_func(date=i,ro_init=ro_init,ro_alpha=ro_alpha,r0_delta=r0_delta,time_shift=time_shift,time_shift2=time_shift2,time_shift3=time_shift3) for i in dates]
   return dates,r0
 if plot:
  dates=pd.date_range('2021-02-01','2021-06-10').to_pydatetime()
  r0=[r0_func(date=i,ro_init=ro_init,ro_alpha=ro_alpha,r0_delta=r0_delta,time_shift=time_shift,time_shift2=time_shift2,time_shift3=time_shift3) for i in dates]
  rr=pd.DataFrame({'dates':dates,'r0':r0})
  pylab.close()
  pylab.plot_date(rr.dates,rr.r0);pylab.show()
  return
 init_date=datetime.datetime(2021, 2, 10, 0, 0); alpha_date=datetime.datetime(2021, 3, 15, 0, 0); delta_date=datetime.datetime(2021, 4, 10, 0, 0);
 if time_shift: 
   init_date+=datetime.timedelta(days=time_shift)
   alpha_date+=datetime.timedelta(days=time_shift)
   delta_date+=datetime.timedelta(days=time_shift)
 if time_shift2:    
   alpha_date+=datetime.timedelta(days=time_shift2)
 if time_shift3:    
   delta_date+=datetime.timedelta(days=time_shift3)
   
 
 if date<init_date: return ro_init
 elif (date>=init_date) and (date<alpha_date): 
  slope=(ro_alpha-ro_init)/float((alpha_date-init_date).days)
  gap=(date-init_date).days
  # ~ print('found %d gap from alpha to init' %(gap))
  return ro_init+(gap*slope)
 elif (date>=alpha_date) and (date<delta_date): 
  slope=(r0_delta-ro_alpha)/float((delta_date-alpha_date).days)
  gap=(date-alpha_date).days
  # ~ print('found %d gap from delta to alpha' %(gap))
  return ro_alpha+(gap*slope)
 elif date>=delta_date: return r0_delta
def reinfection_rate_func(date='',reinfection_rate_init=0.10,reinfection_rate_alpha=0.12,reinfection_rate_delta=0.35,time_shift=0,time_shift2=0,time_shift3=0):
 init_date=datetime.datetime(2021, 2, 10, 0, 0); alpha_date=datetime.datetime(2021, 3, 15, 0, 0); delta_date=datetime.datetime(2021, 4, 10, 0, 0);
 
 if time_shift: 
   init_date+=datetime.timedelta(days=time_shift)
   alpha_date+=datetime.timedelta(days=time_shift)
   delta_date+=datetime.timedelta(days=time_shift)
 if time_shift2:    
   alpha_date+=datetime.timedelta(days=time_shift2)
 if time_shift3:    
   delta_date+=datetime.timedelta(days=time_shift3)
 
 if date<init_date: return reinfection_rate_init
 elif (date>=init_date) and (date<alpha_date): 
  slope=(reinfection_rate_alpha-reinfection_rate_init)/float((alpha_date-init_date).days)
  gap=(date-init_date).days
  # ~ print('found %d gap from alpha to init' %(gap))
  return reinfection_rate_init+(gap*slope)
 elif (date>=alpha_date) and (date<delta_date): 
  slope=(reinfection_rate_delta-reinfection_rate_alpha)/float((delta_date-alpha_date).days)
  gap=(date-alpha_date).days
  # ~ print('found %d gap from delta to alpha' %(gap))
  return reinfection_rate_alpha+(gap*slope)
 elif date>=delta_date: return reinfection_rate_delta
 
def rest(R0=7.5,startdate='2021-04-20',enddate='2021-06-04',orig_infected_percent=0.65,max_cdr=14,min_cdr=10): 
 pop=20e6 
  
 d,p=zip(*get_positivity('dl'))
 
 #get r0
 dates2=[i for i in d if i>datetime.datetime.strptime(startdate,'%Y-%m-%d') and i<datetime.datetime.strptime(enddate,'%Y-%m-%d')]
 r0=[r0_func(i) for i in dates2]
 
 #get cdr from TPR
 xx=pd.DataFrame({'dates':d,'p':p})
 dates=xx[(xx.dates>startdate) & (xx.dates<enddate)].dates
 p=xx[(xx.dates>startdate) & (xx.dates<enddate)].p
 cdr=np.array([cdr_func(i,max_cdr,min_cdr) for i in p])
 
 d,c=zip(*get_cases('dl',case_type='confirmed',return_full_series=True))
 xx=pd.DataFrame({'dates':d[1:],'cases':np.diff(c)})
 # ~ prev=xx[(xx.dates>'2021-04-20') & (xx.dates<'2021-06-04')].cases*cdr_ratio
 num_infected=xx[(xx.dates>startdate) & (xx.dates<enddate)].cases*(100/cdr)
 prev_daily=num_infected/pop
 dates=xx[(xx.dates>startdate) & (xx.dates<enddate)].dates
 
 
 # ~ print(len(dates))
 
 
 prev=[];
 for idx in range(len(prev_daily)): 
   tot_infected_percent_till_date=(prev_daily[:idx+1].sum())+orig_infected_percent
   if tot_infected_percent_till_date>0.90: tot_infected_percent_till_date=0.90
   prev.append(tot_infected_percent_till_date)
 prev=pd.DataFrame(prev)[0]
 # ~ return prev
 
 dt,recr,groc_phar,parks,trans,wrksp,resi,avg=zip(*get_mobility('dl',do_moving_average=True))
 m=pd.DataFrame({'dates':dt,'avg':avg})
 # ~ m=pd.DataFrame({'dates':dt,'avg':recr})
 mobility=m[(m.dates>startdate) & (m.dates<enddate)].avg*0.01
 # ~ return mobility
 #Rt=(1-(prev2+0.7))*(1-reduction)*R0
 
 a=(1-prev) 
 b=mobility+1
 # ~ Rt=a.values*b.values*R0
 Rt=a.values*b.values*np.array(r0)
 return Rt,a,b,dates,prev,prev_daily,r0

def rweekly(state='',district='',days=6,startdate='2021-01-01',use_tpr=False):
 if len(state)==2 and state in state_code_to_name: x=state;state=state_code_to_name[state];
 if state in ['','India']:
  x=pd.DataFrame(get_cases_national('confirmed'),columns=['dates','cases'])
  # ~ x=x[x.dates>=startdate]
  if use_tpr:
    z=[i for i in get_positivity(state) if i[0]>=datetime.datetime.strptime(startdate,'%Y-%m-%d')]
    d,c=zip(*z)
    x=pd.DataFrame({'dates':d,"cases":c})
 else:
   if district: 
    d,c=zip(*get_cases_district(state,district,case_type='confirmed'))
    x=pd.DataFrame({'dates':d,"cases":c})
    x=x[x.dates>=startdate]
   else:
    if use_tpr:
      z=[i for i in get_positivity(state) if i[0]>=datetime.datetime.strptime(startdate,'%Y-%m-%d')]
      d,c=zip(*z)
      x=pd.DataFrame({'dates':d,"cases":c})
    else:
      z=[i for i in get_cases(state,case_type='confirmed',return_full_series=True) if i[0]>=datetime.datetime.strptime(startdate,'%Y-%m-%d')]
      d,c=zip(*z)
      c=np.diff(c);d=d[1:];  x=pd.DataFrame({'dates':d,"cases":c})
 c=moving_average(x.cases)
 rout=[]
 for idx in range(days,len(c)):
  fact=float(c[idx])/c[idx-days]
  rout.append((x.dates[idx],fact))
 rout=pd.DataFrame(rout,columns=['dates','r'])
 return rout

def rmodel(model_city='dl',r0_time_shift=0,r0_time_shift2=0,r0_time_shift3=0,cdr0=10.0,init_prev=0.55,reinfection_rate_delta=0.25,GT=6,mobility_shift='',startdate='2021-02-15',enddate='2021-06-08',plot=True):
  tot_pop=20e6;  startdate=datetime.datetime.strptime(startdate,"%Y-%m-%d");
  enddate=datetime.datetime.strptime(enddate,"%Y-%m-%d")
  
  import math;delta_days=(enddate-startdate).days
  
  #get IO
  if model_city in ['dl']:
    d,c=zip(*get_cases('dl',case_type='confirmed',return_full_series=True));    c=np.diff(c);d=d[1:];  
  elif model_city in ['bg']:
    d,c=zip(*get_cases_district('ka','Bengaluru Urban',case_type='confirmed',return_full_series=True))
    tot_pop=12e6
  elif model_city in ['ch']:
    d,c=zip(*get_cases_district('tn','Chennai',case_type='confirmed',return_full_series=True))
    tot_pop=10.9e6
  elif model_city in ['ah']:
    d,c=zip(*get_cases_district('gj','Ahmedabad',case_type='confirmed',return_full_series=True))
    tot_pop=9e6
  x=pd.DataFrame({'dates':d,"cases":c})
  c=moving_average(x.cases);cases_dict=dict(zip(d,c))
  I0=cases_dict[startdate]*(100./cdr0)
  #get mobilility
  if model_city in ['dl']:
    dt,recr,groc_phar,parks,trans,wrksp,resi,avg=zip(*get_mobility('dl',do_moving_average=True,special_sum=False))
  elif model_city in ['bg']:
    dt,recr,groc_phar,parks,trans,wrksp,resi,avg=zip(*get_mobility('ka','Bangalore Urban',do_moving_average=True,special_sum=False))
  elif model_city in ['ch']:    
    dt,recr,groc_phar,parks,trans,wrksp,resi,avg=zip(*get_mobility('tn','Chennai',do_moving_average=True,special_sum=False))
  elif model_city in ['ah']:    
    dt,recr,groc_phar,parks,trans,wrksp,resi,avg=zip(*get_mobility('gj','Ahmedabad',do_moving_average=True,special_sum=False))
  
  if mobility_shift:
    if mobility_shift>0:      
      mobility_dict=dict(zip(dt[mobility_shift:],avg[:-1*mobility_shift]))
    elif mobility_shift<0:
      mobility_shift=-1*mobility_shift      
      mobility_dict=list(zip(dt[:-1*mobility_shift],avg[mobility_shift:]))
      mobility_dict.extend(list(zip(dt[-1*mobility_shift:],[avg[-1]]*mobility_shift)))
      mobility_dict=dict(mobility_dict)
  else:
    # ~ mobility_dict=dict(zip(dt,avg))
    mobility_dict=dict(zip(dt,recr))
  rt0=r0_func(startdate,time_shift=r0_time_shift,time_shift2=r0_time_shift2,time_shift3=r0_time_shift3)*(1-init_prev)*(1+(0.01*mobility_dict[startdate]))
  rt=[rt0];dates=[startdate];daily_infections=[I0]
  prev_pop_daily=[0]
  
  for i in range(1,delta_days):
   date=startdate+datetime.timedelta(days=i)  
   try:
     infections_new=(daily_infections[-1])*math.pow(rt[-1],1/GT)
   except:
     print('got error ',daily_infections[-1],rt[-1],1/GT,i,date)
     return dates,daily_infections,prev_pop_daily,rt
   daily_infections.append(infections_new);dates.append(date)
   
   cur_reinfection_rate=reinfection_rate_func(date,reinfection_rate_delta=reinfection_rate_delta,time_shift=r0_time_shift,time_shift2=r0_time_shift2,time_shift3=r0_time_shift3)
   prev_pop_immunity=(1-cur_reinfection_rate)*(float(sum(daily_infections))/tot_pop)
   prev_pop_daily.append(prev_pop_immunity)
   prev=init_prev+prev_pop_immunity
   mobility=0.01*mobility_dict[date]
   r0t=r0_func(date,time_shift=r0_time_shift,time_shift2=r0_time_shift2,time_shift3=r0_time_shift3)
   rt_new=r0t*(1-prev)+(1+mobility) 
   # ~ rt_new=r0_func(date)*(1-prev)+(1+mobility) 
   rt.append(rt_new) 
   rt[-1]=r0t*(1-prev)*(1+mobility)
   # ~ if len(rt)==2: 
     # ~ print(rt,'rt_new',rt_new,r0_func(date)*(1-prev)*(1+mobility))
     # ~ rt[-1]=r0_func(date)*(1-prev)*(1+mobility)
     # ~ print('rt',rt)
  
  if plot:
    if model_city in ['dl']:      rw=rweekly('dl',startdate=startdate.strftime('%Y-%m-%d'),days=GT);
    elif model_city in ['bg']:      rw=rweekly('ka','Bengaluru Urban',startdate=startdate.strftime('%Y-%m-%d'),days=GT);
    elif model_city in ['ch']:      rw=rweekly('tn','Chennai',startdate=startdate.strftime('%Y-%m-%d'),days=GT);
    elif model_city in ['ah']:      rw=rweekly('gj','Ahmedabad',startdate=startdate.strftime('%Y-%m-%d'),days=GT);
    # ~ rcalc=rw[(rw.dates>startdate) & (rw.dates<enddate)].r.values;
    rcalc=rw[rw.dates>startdate].r.values;
    rdates=pd.date_range(startdate,periods=len(rcalc)+1)[1:].to_pydatetime()
    # ~ plotex(dates,rt,dates[1:],rcalc,label='Calculated Rt',label2='measured Rt (%d-day change)' %(GT),color2='green',state=model_city.upper())
    plotex(dates,rt,rdates,rw[rw.dates>startdate].r.values,label='Calculated Rt',label2='measured Rt (%d-day change)' %(GT),color2='green',state=model_city.upper())
    sp,ax=pylab.subplots()
    locator = mdates.AutoDateLocator(minticks=3, maxticks=7);formatter = mdates.ConciseDateFormatter(locator);ax.xaxis.set_major_locator(locator);ax.xaxis.set_major_formatter(formatter)
    ax.semilogy(d[-130:],c[-130:],label='Daily cases')
    ax.semilogy(dates,daily_infections,label='Daily infections')
    pylab.legend();pylab.xlabel('Dates');pylab.ylabel('Cases/Infections in '+model_city.upper());pylab.title('Cases vs infections in '+model_city);
    pylab.savefig(TMPDIR+'Log-scale cases vs infections in '+model_city.upper()+'.jpg');pylab.close()
    
  return dates,daily_infections,prev_pop_daily,rt

def plot_func(R0=8,startdate='2021-04-20',enddate='2021-06-04',gt=6,orig_infected_percent=0.60,max_cdr=10,min_cdr=9):
 
 y=rest(R0=R0,startdate=startdate,enddate=enddate,orig_infected_percent=orig_infected_percent,max_cdr=max_cdr,min_cdr=min_cdr);
 a=y[1];b=y[2];r0=y[6]
 # ~ return (a,b,r0)
 rw=rweekly('dl',days=gt);rcalc=rw[(rw.dates>startdate) & (rw.dates<enddate)].r.values;
 rcalc=pd.DataFrame({'dates':y[3],'r':rcalc})
 rr=pd.DataFrame({'dates':y[3],'r':y[0]});
 pylab.close();sp,ax=pylab.subplots()
 locator = mdates.AutoDateLocator(minticks=3, maxticks=7);formatter = mdates.ConciseDateFormatter(locator);ax.xaxis.set_major_locator(locator);ax.xaxis.set_major_formatter(formatter)
 # ~ pylab.plot(rcalc.dates,rcalc.r,label='5-day cases growth rate (measured Rt)');pylab.plot(rr.dates,rr.r,label='Calculated Rt for simplified homogeneous network');
 pylab.plot(rw[rw.dates>startdate].dates,rw[rw.dates>startdate].r,label=str(gt)+'-day cases growth rate (measured Rt)');pylab.plot(rr.dates,rr.r,label='Calculated Rt for simplified homogeneous network');
 pylab.plot(rcalc.dates,np.ones(len(rcalc.dates)),label='Rt=1')
 pylab.legend();pylab.xlabel('Date');pylab.ylabel('Rt')
 pylab.show()
 

def make_plots(use_all_states=False,use_solid_lines=False):
  # ~ import pylab
  # ~ states_icu=['Punjab','Haryana','Kerala','Telangana','Karnataka']
  states_icu=['Punjab','Haryana','Kerala']
  states_ventilator=['Punjab','Haryana','Kerala']


  #make ICU plot
  for state in states_icu:
    icu_data=get_people_in_icus(state)
    if not icu_data: continue
    dates=[i[0] for i in icu_data]
    dates=[datetime.datetime.strptime(i,'%d/%m/%Y') for i in dates]
    dates=pylab.date2num(dates)
    icu_percent=[i[1] for i in icu_data]
    if use_solid_lines:
      pylab.plot_date(dates,icu_percent,'-',label=state)
    else:
      pylab.plot_date(dates,icu_percent,label=state)
  pylab.xlabel('date');pylab.ylabel('percent of active cases in ICU');pylab.legend()
  pylab.title('ICU use in states over time')
  pylab.show();
  # ~ #make ventilator plot
  for state in states_ventilator:
    ventilator_data=get_people_on_ventilators(state)
    if not ventilator_data: continue
    dates=[i[0] for i in ventilator_data]    
    dates=[datetime.datetime.strptime(i,'%d/%m/%Y') for i in dates]
    dates=pylab.date2num(dates)
    ventilator_percent=[i[1] for i in ventilator_data]
    if use_solid_lines:
      pylab.plot_date(dates,ventilator_percent,'-',label=state)
    else:
      pylab.plot_date(dates,ventilator_percent,label=state)
  pylab.xlabel('date');pylab.ylabel('percent of active cases on ventilator');pylab.legend()
  pylab.title('Ventilator use in states over time')
  pylab.show(); 
  



    
if __name__=='__main__':
  make_plots()


