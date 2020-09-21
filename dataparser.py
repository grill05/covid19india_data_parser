#!/usr/bin/python2

#code runs with python-2 (for python-3, just convert the "print" statements to function
#to install dependencies "pip install pylab json requests"

# ~ for moving average with window 'N'
# ~ np.convolve(x, np.ones((N,))/N, mode='valid')

import os,sys,copy
import json,datetime,numpy,requests,colorama
datetime_doa_marker=datetime.datetime(2020, 1, 1, 0, 0)

state_code_to_name={'pb':'Punjab',            'hr':'Haryana',
                    'kl':'Kerala',            'ka':'Karnataka',
                    'tg':'Telangana',         'gj':'Gujarat',
                    'dl':'Delhi',             'nl':'Nagaland',
                    'sk':'Sikkim',            'ct': 'Chhattisgarh',
                    'ap':'Andhra Pradesh',    'tn': 'Tamil Nadu',
                    'br':'Bihar',             'up': 'Uttar Pradesh',
                    'as':'Assam',             'wb': 'West Bengal',
                    'mp':'Madhya Pradesh',    'jh': 'Jharkhand',
                    'rj':'Rajasthan',         'or': 'Odisha',
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

##date must be given as 01/09/2020 for September 1,2020
##State must be fullname (see dict above)
def get_cases(state='Telangana',date='01/09/2020',case_type='active',return_full_series=False,verbose=False):
  x=json.load(open('states_daily.json'))['states_daily']

  target_datetime=datetime.datetime.strptime(date,'%d/%m/%Y')
  state_code=state_name_to_code[state]

  #get all confirmed cases till date
  confirmed=0;recovered=0;deaths=0;active=0;

  if return_full_series:
    confirmed_series={};recovered_series={};deaths_series={};active_series={};
    target_datetime=datetime.datetime.strptime(x[-1]['date'].replace('-20','-2020'),'%d-%b-%Y');#choose last date available
    
  for i in x:
    datetime_i=datetime.datetime.strptime(i['date'].replace('-20','-2020'),'%d-%b-%Y')
    if datetime_i<=target_datetime:
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
    
  if case_type=='active':
    if verbose: print 'Active cases in %s on %s were %d' %(state,date,active)
    if return_full_series:  return active_series
    else:                   return active
  elif case_type=='confirmed':
    if verbose: print 'Total cases in %s on %s were %d' %(state,date,confirmed)
    if return_full_series:  return confirmed_series
    else:                   return confirmed
  elif case_type=='recovered':
    if verbose: print 'Recovered cases in %s on %s were %d' %(state,date,recovered)
    if return_full_series:  return recovered_series
    else:                   return recovered
  elif case_type=='deaths':
    if verbose: print 'Deaths in %s on %s were %d' %(state,date,deaths)
    if return_full_series:  return deaths_series
    else:                   return deaths


#cache this to avoid repeated file reads
global_karnataka_case_series=get_cases(state='Karnataka',case_type='confirmed',return_full_series=True,verbose=False)
global_karnataka_case_date_series=[i[0] for i in global_karnataka_case_series]
global_karnataka_case_number_series=[i[1] for i in global_karnataka_case_series]
  
def highlight(text):
  highlight_begin=colorama.Back.BLACK+colorama.Fore.WHITE+colorama.Style.BRIGHT
  highlight_reset=colorama.Back.RESET+colorama.Fore.RESET+colorama.Style.RESET_ALL
  return highlight_begin+text+highlight_reset
def helper_download_karnataka_bulletin(twitter_link,debug=False):
  x=requests.get(twitter_link)
  url=x.url
  file_id=url.split('/d/')[1].split('/')[0]
  google_drive_url='https://docs.google.com/uc?export=download&id='+file_id
  download_cmd='wget -q --no-check-certificate "'+google_drive_url+'" -O tmp.pdf'
  if debug: print download_cmd
  os.system(download_cmd)
  (bulletin_date,annex_range)=karnataka_bulletin_parser('tmp.pdf',return_date_only=True)
  if debug: print 'bulletin_date: '+str(bulletin_date)
  if not bulletin_date:
    print 'could not find date for bulletin. Using tmp format'
    bulletin_date_string=datetime.datetime.now().strftime('%H-%s')
  else:    
    bulletin_date_string=datetime.datetime.strftime(bulletin_date,'%m_%d_%Y')
  os.system('cp -v tmp.pdf "'+bulletin_date_string+'.pdf"')

def helper_download_delhi_bulletin(link,debug=False):
  download_cmd='wget -q --no-check-certificate "'+link+'" -O tmp.pdf'
  if debug: print download_cmd
  os.system(download_cmd)
  bulletin_date=delhi_bulletin_parser('tmp.pdf',return_date_only=True)
  if debug: print 'bulletin_date: '+str(bulletin_date)
  if not bulletin_date:
    print 'could not find date for bulletin. Using tmp format'
    bulletin_date_string=datetime.datetime.now().strftime('%H-%s')
  else:    
    bulletin_date_string=datetime.datetime.strftime(bulletin_date,'%m_%d_%Y')
  os.system('cp -v tmp.pdf "'+bulletin_date_string+'.pdf"')




def delhi_bulletin_parser(bulletin='09_15_2020.pdf',return_date_only=False):
  cmd='pdftotext -layout "'+bulletin+'" tmp.txt';os.system(cmd)
  b=[i.strip() for i in open('tmp.txt').readlines() if i.strip()]

  date_string=[i for i in b if '2020' in i]
  if not date_string:
    print 'could not find date for bulletin ',bulletin
    return
  date_string=date_string[0].lower()
  try:
    if '/' in date_string:
      date_string=date_string.split('/')[1].replace(')','').replace('(','').replace(',',' ').replace('2020',' ').strip()
    else:
      date_string=date_string.replace(')','').replace('(','').replace(',',' ').replace('2020',' ').strip()
  except:
    print 'error getting date for bulletin: '+bulletin+' with string: '+date_string
  # ~ print date_string
  if len(date_string.split())==1: #all jumbled        
    for mm in ['june','july','august','september']: date_string=date_string.replace(mm,'')
    day=date_string
    month_string=date_string.split()[0].strip().lower()
    # ~ print date_string,month_string
    month_string=month_string[:month_string.index(date_string)]
  else:
    day=date_string.split()[1]
    month_string=date_string.split()[0].strip().lower()
  day=day.replace('th','').replace('nd','').replace('st','').replace('rd','').strip()
  day=int(day)
  
  
  month=9
  if 'august' in month_string: month=8
  elif 'july' in month_string: month=7
  elif 'june' in month_string: month=6

  date=datetime.datetime(2020,month,day,0,0)

  if return_date_only: return date

  hos=[i for i in b if i.lower().startswith('hospital')]
  if not hos:
    print 'could not find data in bulletin %s for covid hospitals' %(bulletin)
    return
  hos=hos[0];hos_capacity=hos.split()[-3];hos_used=hos.split()[-2];

  dcc=[i for i in b if i.lower().startswith('dedicated covid care centre')]
  if not dcc:
    print 'could not find data in bulletin %s for DCCC' %(bulletin)
    return
  dcc=dcc[0];dcc_capacity=dcc.split()[-3];dcc_used=dcc.split()[-2];

  dchc=[i for i in b if i.lower().startswith('dedicated covid health')]
  if not dchc:
    print 'could not find data in bulletin %s for DCHC' %(bulletin)
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
      print 'could not find data in bulletin %s for RTPCR' %(bulletin)
      return
    rtpcr=rtpcr[0].split()[-1]

    rapid=[i for i in b if i.lower().startswith('rapid antigen')]
    if not rapid:
      print 'could not find data in bulletin %s for rapid tests' %(bulletin)
      return
    rapid=rapid[0].split()[-1]
    total=int(rapid)+int(rtpcr)

  cz=[i for i in b if 'number of containment zones' in i.lower()]
  if not cz:
    print 'could not find data in bulletin %s for containment zones' %(bulletin)
    return
  cz=cz[0].split()[-1].split(':')[-1].split('\x93')[-1]

  amb=[i for i in b if 'ambulance' in i.lower()]
  if not amb:
    print 'could not find data in bulletin %s for ambulances' %(bulletin)
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
      print 'could not parse delhi_bulletin: '+pdf
  #manually add data for malformed bulletin days (aug 29,30 and sep 9)
  do.append(delhi_status(datetime.datetime(2020,8,29,0,0),14143, 3966, 10143, 821, 594, 275, 22004,6597,15407,803,1371))
  do.append(delhi_status(datetime.datetime(2020,8,30,0,0),14145, 4030, 10143, 876, 599, 336, 20437,6881,13556,820,1319))
  # ~ do.append(delhi_status(datetime.datetime(2020,6,9,0,0),8872, 4680, 285, 187, 6038, 1414, 54517,0,0,0,0))
  do.sort(key= lambda y: y.date)
  return do

def delhi_analysis(do):
  #hos_capacity='';hos_used='';dcc_capacity='';dcc_used='';dchc_capacity='';dchc_used='';
  # ~ hos_util=0;dcc_util=0;dchc_util=0
  # ~ total='';rtpcr='';rapid='';
  # ~ cz='';amb='';date=''
  import pylab
  dates=pylab.date2num([i.date for i in do])
  hos_used=[i.hos_used for i in do]
  dhc_used=[i.dchc_used for i in do]  
  dcc_used=[i.dcc_used for i in do]
  
  tot=[i.total for i in do]
  r=[i.rapid for i in do]
  rtpcr=[i.rtpcr for i in do]
  rp=numpy.float64(r)/numpy.float64(tot)

  cz=[i.cz for i in do]

  actives=get_cases(state='Delhi',case_type='active',return_full_series=True,verbose=True)
  deaths=get_cases(state='Delhi',case_type='deaths',return_full_series=True,verbose=True)
  dates2=pylab.date2num([i[0] for i in actives])

  actives=[i[1] for i in actives if i[0]>=datetime.datetime(2020, 6, 18, 0, 0) and i[0]<=datetime.datetime(2020, 9, 15, 0, 0)]
  
  deaths=numpy.diff([i[1] for i in deaths if i[0]<=datetime.datetime(2020, 9, 15, 0, 0)])#have more
  deaths=moving_average(deaths)
  dates_skip=5; #have anomaly of sudden addition in mid-June
  deaths=deaths[-1*len(dates):]
   
  

  hp=100*(numpy.float64(hos_used)/numpy.float64(actives))
  dhp=100*(numpy.float64(dhc_used)/numpy.float64(actives))
  ccp=100*(numpy.float64(dcc_used)/numpy.float64(actives))
  
  sp,ax=pylab.subplots()

  color = 'tab:blue'
  ax.set_xlabel('Date')
  ax.set_ylabel('Hospitalization (DCH) Percent (of active cases)',color=color)
  ax.plot_date(dates,hp,color=color,label='Hospitalization Percentage')
  ax.tick_params(axis='y', labelcolor=color)  

  ax2=ax.twinx()
  color = 'tab:green'
  ax2.set_ylabel('Health Center (DCHC) Percent (of active cases)',color=color)
  ax2.plot_date(dates,dhp,color=color,label='Health Center Percentage')
  ax2.tick_params(axis='y', labelcolor=color)

  sp.tight_layout()

  title='Hospitalion-percent(of actives) vs Health center percent in Delhi'
  pylab.title(title);
  ax2.legend(loc='upper right'); ax.legend(loc='upper left');
  pylab.legend();
  pylab.show()
  # ~ sp,ax=pylab.subplots()

  # ~ color = 'tab:blue'
  # ~ ax.set_xlabel('Date')
  # ~ ax.set_ylabel('Hospitalization Percent (of active cases)',color=color)
  # ~ ax.plot_date(dates,hp,color=color,label='Hospitalization Percentage')
  # ~ ax.tick_params(axis='y', labelcolor=color)  

  # ~ ax2=ax.twinx()
  # ~ color = 'tab:green'
  # ~ ax2.set_ylabel('Daily Tests',color=color)
  # ~ ax2.plot_date(dates,tot,color=color,label='Daily Tests')
  # ~ ax2.tick_params(axis='y', labelcolor=color)

  # ~ sp.tight_layout()

  # ~ title='Hospitalion-percent(of actives) vs Daily-tests in Delhi'
  # ~ pylab.title(title);
  # ~ ax2.legend(loc='upper right'); ax.legend(loc='upper left');
  # ~ pylab.legend();
  # ~ pylab.show()

  # ~ sp,ax=pylab.subplots()

  # ~ color = 'tab:blue'
  # ~ ax.set_xlabel('Date')
  # ~ ax.set_ylabel('Hospital beds used',color=color)
  # ~ ax.plot_date(dates,hos_used,color=color,label='Hospital Beds')
  # ~ ax.tick_params(axis='y', labelcolor=color)  
  # ~ ax.legend(loc='upper left');
  
  # ~ ax2=ax.twinx()
  # ~ color = 'tab:orange'
  # ~ ax2.set_ylabel('Active Cases',color=color)
  # ~ ax2.plot_date(dates,actives,color=color,label='Active Cases')
  # ~ ax2.tick_params(axis='y', labelcolor=color)
  # ~ ax2.legend(loc='lower left');
  
  # ~ sp.tight_layout()

  # ~ title='Hospital-beds-used vs Active-Cases in Delhi'
  # ~ pylab.title(title);
  # ~ ax2.legend(loc='upper right'); 

  # ~ sp,ax=pylab.subplots()

  # ~ color = 'tab:blue'
  # ~ ax.set_xlabel('Date')
  # ~ ax.set_ylabel('Number of Containment Zones',color=color)
  # ~ ax.plot_date(dates,cz,color=color,label='Containment Zones')
  # ~ ax.tick_params(axis='y', labelcolor=color)  
  # ~ ax.legend(loc='upper left');
  
  # ~ ax2=ax.twinx()
  # ~ color = 'tab:orange'
  # ~ ax2.set_ylabel('Active Cases',color=color)
  # ~ ax2.plot_date(dates,actives,color=color,label='Active Cases')
  # ~ ax2.tick_params(axis='y', labelcolor=color)
  # ~ ax2.legend(loc='lower left');
  
  # ~ sp.tight_layout()

  # ~ title='Containment-Zones vs Active-Cases in Delhi'
  # ~ pylab.title(title);
  # ~ ax2.legend(loc='upper right'); 

  # ~ sp,ax=pylab.subplots()

  # ~ color = 'tab:blue'
  # ~ ax.set_xlabel('Date')
  # ~ ax.set_ylabel('Hospital beds used',color=color)
  # ~ ax.plot_date(dates,hos_used,color=color,label='Hospital Beds')
  # ~ ax.tick_params(axis='y', labelcolor=color)  
  # ~ ax.legend(loc='upper left');
  
  # ~ ax2=ax.twinx()
  # ~ color = 'tab:red'
  # ~ ax2.set_ylabel('Daily Deaths (7-day MA)',color=color)
  # ~ ax2.plot_date(dates[dates_skip:],deaths[dates_skip:],color=color,label='Daily Deaths (7-day MA)')
  # ~ ax2.tick_params(axis='y', labelcolor=color)
  # ~ ax2.legend(loc='lower left');
  
  # ~ sp.tight_layout()

  # ~ title='Hospital-beds-used vs Daily-deaths in Delhi'
  # ~ pylab.title(title);
  # ~ ax2.legend(loc='upper right'); 
  # ~ sp,ax=pylab.subplots()

  # ~ color = 'tab:blue'
  # ~ ax.set_xlabel('Date')
  # ~ ax.set_ylabel('Active Cases',color=color)
  # ~ ax.plot_date(dates,actives,color=color,label='Active Cases')
  # ~ ax.tick_params(axis='y', labelcolor=color)  
  # ~ ax.legend(loc='upper left');
  
  # ~ ax2=ax.twinx()
  # ~ color = 'tab:red'
  # ~ ax2.set_ylabel('Daily Deaths (7-day MA)',color=color)
  # ~ ax2.plot_date(dates[dates_skip:],deaths[dates_skip:],color=color,label='Daily Deaths (7-day MA)')
  # ~ ax2.tick_params(axis='y', labelcolor=color)
  # ~ ax2.legend(loc='lower left');
  
  # ~ sp.tight_layout()

  # ~ title='Active-cases vs Daily-deaths in Delhi'
  # ~ pylab.title(title);
  # ~ ax2.legend(loc='upper right'); 
  sp,ax=pylab.subplots()

  color = 'tab:blue'
  ax.set_xlabel('Date')
  ax.set_ylabel('DCH(hospital) beds',color=color)
  ax.plot_date(dates,hos_used,color=color,label='DCH(hospital) beds')
  ax.tick_params(axis='y', labelcolor=color)  
  ax.legend(loc='upper left');
  
  ax2=ax.twinx()
  color = 'tab:red'
  ax2.set_ylabel('DCHC(Health Center) beds',color=color)
  ax2.plot_date(dates,dhc_used,color=color,label='DCHC(Health Center) beds')
  ax2.tick_params(axis='y', labelcolor=color)
  ax2.legend(loc='lower left');
  
  sp.tight_layout()

  title='Bed Utilization in Delhi\'s Hospitals (DCH) and Health Centers (DCHC) over time'
  pylab.title(title);
  ax2.legend(loc='upper right'); 

  # ~ ax=pylab.figure()
  # ~ pylab.plot_date(dates,tot,label='Total tests')
  # ~ pylab.plot_date(dates,r,label='Rapid antigen tests')
  # ~ xlabel='Date';ylabel='Tests';title='Scale-up of Testing in Delhi over time'
  # ~ pylab.xlabel(xlabel);pylab.ylabel(ylabel);pylab.title(title);pylab.legend()

  # ~ ax=pylab.figure()
  # ~ pylab.plot_date(dates,rp,label='Rapid tests percentage')
  # ~ xlabel='Date';ylabel='Percent of Rapid antigen tests';title='Reliance on rapid tests in Delhi over time'
  # ~ pylab.xlabel(xlabel);pylab.ylabel(ylabel);pylab.title(title);pylab.legend()
  
  return (hos_used,deaths)
  
def update_data_files():
  urls=['https://api.covid19india.org/states_daily.json','https://api.covid19india.org/data.json','https://api.covid19india.org/state_test_data.json']
  for i in urls:
    filename=os.path.split(i)[1]
    if os.path.exists(filename):
      os.remove(filename)
    cmd='wget -q "'+i+'" -O "'+filename+'"';
    print cmd
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
    info+='\tHospital: %d/%d (%.1f percent)\n' %(self.hos_capacity,self.hos_used,self.hos_util)
    info+='\tDCHC: %d/%d (%.1f percent)\n'  %(self.dchc_capacity,self.dchc_used,self.dchc_util)
    info+='\tDCCC: %d/%d (%.1f percent)\n'%(self.dcc_capacity,self.dcc_used,self.dcc_util)
    info+='Tests:\n\tTotal: %d\n' %(self.total)
    if self.rtpcr:
      info+='\tRTPCR: %d\n\tRapid: %d' %(self.rtpcr,self.rapid)
    info+='Misc:\n\tContainment Zones: %d\n\tAmbulance calls: %d' %(self.cz,self.amb)
    print info
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
    if age.isdigit(): self.age=int(age)
    else:             print 'for %s, could not parse age: %s from age_gender string: %s' %(fatality_string,age,age_gender)
    self.gender=age_gender.split(' ')[-1]
      
    if 'who' in ss: #has comorbidity
      district=ss.split('who')[0]
      if 'of' not in district:
        print 'for %s, could not district: %s from ss: %s' %(fatality_string,district,ss)
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
    print info


  
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
    self.age=int(age)
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
        self.admission_death_interval=(self.date_of_death-self.date_of_admission).days
        if self.date_of_detection:
          self.detection_admission_interval=(self.date_of_admission-self.date_of_detection).days    
    if self.date_of_detection:
      self.detection_death_interval=(self.date_of_death-self.date_of_detection).days
    if self.date_of_reporting:
      try:
        self.death_reporting_interval=(self.date_of_reporting-self.date_of_death).days
      except:
        print 'error calculating death_reporting_interval with dor: '+str(self.date_of_reporting)+' and dod '+str(self.date_of_death)
      
  def info(self):
    info_str=''
    if self.patient_number: info_str+='P.no %d ' %(self.patient_number)
    info_str+='District: %s Age: %d Gender: %s Origin: %s\n' %(self.district,self.age,self.gender,self.origin)
    info_str+='Comorbidities: %s\n' %(' '.join(self.comorbidities))
    dod='N/A'
    if self.date_of_detection:
      dod=self.date_of_detection.strftime('%d/%m/%Y')
    doa='';dor='';
    if self.date_of_admission: doa=self.date_of_admission.strftime('%d/%m/%Y')
    if self.date_of_reporting: dor=self.date_of_reporting.strftime('%d/%m/%Y')
    
    info_str+='Detected: %s Admitted: %s Died: %s Reported: %s\n' %(dod,doa,self.date_of_death.strftime('%d/%m/%Y'),dor)
    if self.admission_death_interval: info_str+='admission_death_interval: %d\n' %(self.admission_death_interval)
    if self.detection_admission_interval: info_str+='detection_admission_interval: %d\n' %(self.detection_admission_interval)    
    if self.detection_death_interval: info_str+='detection_death_interval: %d\n' %(self.detection_death_interval)
    if self.death_reporting_interval: info_str+='death_reporting_interval: %d' %(self.death_reporting_interval)
    print info_str.strip()
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
    print info_str
#class meant to represent a discharges patient in Karnataka
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
    print info_str


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
  z=zip(values,freq)
  if sort: z.sort()
  return z
  
def moving_average(input_array=[],window_size=5,index_to_do_ma=1):
  x=input_array
  if type(input_array[0])==tuple:
    x=[i[index_to_do_ma] for i in input_array]
    dates=[i[0] for i in input_array]
    x2=numpy.convolve(x, numpy.ones((window_size,))/window_size, mode='valid')
    d2=dates[window_size-1:]
    return zip(d2,x2)
  else:
    return numpy.convolve(input_array, numpy.ones((window_size,))/window_size, mode='valid')
   

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
      print dates_index, i
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


def tamil_nadu_bulletin_parser(bulletin='',return_page_range=False,clip_bulletin=False,dump_clippings=False):
  cmd='pdftotext  -layout "'+bulletin+'" tmp.txt';os.system(cmd)
  b=[i for i in open('tmp.txt').readlines() if i]
  idx=0;page_count=1;page_range=[];got_start=False
  bulletin_date=''
  bd=[i for i in b if 'media bulletin' in i.lower()]
  bulletin_date_string='';bulletin_date=''
  if bd:
    bulletin_date=bd[0].split('lletin')[1].strip().replace('-','.').replace('/','.')
    bulletin_date_string=bulletin_date
    bulletin_date=datetime.datetime.strptime(bulletin_date,'%d.%m.%Y')
    
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
    print "clipping buletin "+bulletin+"to  page range "+str(page_range)
    cmd='pdfseparate -f '+str(page_range[0])+' -l '+str(page_range[1])+' "'+bulletin+'" tmp-%04d.pdf';os.system(cmd)
    cmd='pdfunite tmp-*pdf joined.pdf';os.system(cmd)
    cmd='mv -fv joined.pdf "'+bulletin+'"';os.system(cmd)

  cmd='pdftotext -nopgbrk  -layout "'+bulletin+'" tmp.txt';os.system(cmd)

  #find clipping of death info
  b=[i.strip() for i in open('tmp.txt').readlines() if i.strip()]
  idx=0;indices=[];b_idx=0
  for i in b:    
    if 'Death Case No' in i:
      idx+=1;indices.append(b_idx)    
    b_idx+=1
  #last elem, assume 10 more lines
  if indices:
    indices.append(indices[-1]+10)
  else:
    print 'ERROR! Could not find clip indices in: '+bulletin

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
    print 'ERROR! Could not find clip indices in: '+bulletin

  deaths=[]

  bulletin_date_string=''
  for j in range(len(indices)-1):
    bulletin_date_string=indices[j][1]
    bulletin_date=datetime.datetime.strptime(bulletin_date_string,'%d.%m.%Y')

    start=indices[j][0];end=indices[j+1][0]
    
    clip=b[start:end]
    death_case_no=clip[0].strip().split('Death Case No')[1].replace(':','').strip().replace('.','')
    cons=' '.join(clip[1:])

    
    try:
      age=cons.split()[1]
    except:
      print 'error splirtting cons: '+cons+' '+str(indices[j])
    if age.lower()=='years': age=cons.split()[0].replace('A','')

    if not age.isdigit():
      if age[0].isdigit(): #starts right but has alpha
        # ~ print 'incorrect age at index: '+str(j)+' with cons: '+cons
        # ~ return
        x0=age[0]
        for j in range(1,len(age)):
          if age[j].isdigit(): x0+=age[j]
        age=x0
      else:
        if 'year' in cons and 'years' not in cons:
          print 'incorrect age at index: '+str(j)+' with cons: '+cons
          return
        age=cons.lower().split('year')[0].split()[-1]
        if not age.isdigit():
          print age
          print 'could find find age for '+cons
          return
    # ~ death_case_no=int(death_case_no);age=int(age)
    gender=''
    if 'old' in cons:
      try:
        gender=cons.split('old')[1].split()[0].strip()
      except:
        print 'error splitingg gender, cons: '+cons
        return
        
    else:
      if 'years' in cons.lower():
        gender=cons.lower().split('years')[1].split()[0].strip()
      elif 'year' in cons.lower():
        gender=cons.lower().split('year')[1].split()[0].strip()
      else:
        print 'no "old" or "years" for gender in  cons: '+cons
        return
    gender=gender.replace(',','')
    
    
    if 'female' in gender.lower(): gender='F'
    elif 'male' in gender.lower(): gender='M'
    
    district=''
    try:
      district=cons.lower().split('from')[1].split()[0].strip().lower().replace(',','')
    except:
      print '\nerror in getting district for cons: '+cons
      return
      
    
    cons=cons.replace('admiitted on','admitted on'); #fix typo
    doa_eq_dod=False
    date_of_admission=''
    if 'admitted' in cons:
      if 'admitted with' in cons and 'admitted on' not in cons:
        try:
          date_of_admission=cons.split('admitted')[1].split(' on ')[1].strip().split()[0].strip()
        except:
          print 'error getting doa with cons: '+cons
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
      print 'error finding dod from cons: '+cons
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
      print 'error creating datetimes with doa: '+date_of_admission+' with date_of_death: '+date_of_death+'\ncons: '+cons
      return
    try:
      date_of_death=date_of_death.replace('/','.').replace('-','.')
      dod=datetime.datetime.strptime(date_of_death,'%d.%m.%Y')
    except:
      print 'error getting dod with date_of_death: '+date_of_death+'\ncons: '+cons

    
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
    
  
  print len(indices)-1,' death cases found'
  return deaths
  
def karnataka_bulletin_get_margins_confirmed(bulletin='06_18_2020.pdf',page_range=(5,12),execute=True,debug_clip='',debug=False):
  cmd='pdftotext -x 0 -y 0 -W 1000 -H 2000 -bbox-layout -nopgbrk -layout -f '+str(page_range[0])+' -l '+str(page_range[1])+' "'+bulletin+'" tmp.txt';os.system(cmd)
  from bs4 import BeautifulSoup
  soup=BeautifulSoup(open('tmp.txt').read(),'lxml')
  d_idx=[i for i in range(len(soup('block'))) if soup('block')[i]('word')[0].text.strip().lower()=='district']  
  if not d_idx:
    print 'could not find "block" for District in '+bulletin+' with range '+str(page_range)
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
    print 'could not find block for history'
    return
  else:
    history=history[0];d=history
    xmin=float(d.get('xmin'));  xmax=float(d.get('xmax'))
    bboxes['history']=(xmin,xmax)

  #isolated
  isolated=[i for i in hblocks if i.text.strip().startswith('Isolated')]
  if not isolated: isolated=[i for i in hwords if i.text.startswith('Isolated')]
  if not isolated:
    print 'could not find block for isolated'
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
      print 'could not find margins(confirmed) for bulletin: '+ str(bulletin)
      return
    w=str(xcut)
    cmd='pdftotext -x 0  -W '+w+' -y 0 -H 1000  -nopgbrk -layout -f '+str(page_range[0])+' -l '+str(page_range[1])+' '+bulletin+' tmp.txt'
    if debug_clip: print cmd
    os.system(cmd)
    if debug_clip: print 'created debug clip in tmp.txt '
  return xcut
  
def karnataka_bulletin_get_margins(bulletin='09_09_2020.pdf',page_range=(19,23),debug_clip='',debug=False):
  cmd='pdftotext -x 0 -y 0 -W 1000 -H 2000 -bbox-layout -nopgbrk -layout -f '+str(page_range[0])+' -l '+str(page_range[1])+' "'+bulletin+'" tmp.txt';os.system(cmd)
  from bs4 import BeautifulSoup
  soup=BeautifulSoup(open('tmp.txt').read(),'lxml')
  d_idx=[i for i in range(len(soup('block'))) if soup('block')[i]('word')[0].text.strip().lower()=='district']  
  if not d_idx:
    print 'could not find "block" for District in '+bulletin+' with range '+str(page_range)
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
    print 'could not find block for serial number'
    return
  else:
    sno=sno[0];d=sno
    xmin=float(d.get('xmin'));  xmax=float(d.get('xmax'))
    bboxes['sno']=(xmin,xmax)

  #district
  district=[i for i in hblocks if i.text.strip().startswith('District')]
  if not district:
    print 'could not find block for district'
    return
  else:
    district=district[0];d=district
    xmin=float(d.get('xmin'));  xmax=float(d.get('xmax'))
    bboxes['district']=(xmin,xmax)
  
  #State P No
  spno=[i for i in hblocks if i.text.strip().startswith('State')]
  if not spno:
    print 'could not find block for State P. no'
    return
  else:
    spno=spno[0];d=spno
    xmin=float(d.get('xmin'));  xmax=float(d.get('xmax'))
    bboxes['spno']=(xmin,xmax)

  #age
  age=[i for i in hblocks if i.text.strip().startswith(('Age','Ag'))]
  # ~ age=[i for i in hblocks if i.text.strip().startswith(('Age')]
  if not age:
    print 'could not find block for Age'
    return
  else:
    age=age[0];d=age
    xmin=float(d.get('xmin'));  xmax=float(d.get('xmax'))
    bboxes['age']=(xmin,xmax)

  #sex
  sex=[i for i in hblocks if i.text.strip().startswith('Sex')]
  if not sex: sex=[i for i in hwords if i.text.strip().startswith('Sex')]
  if not sex:    
    print 'could not find block for sex'
    return
  else:
    sex=sex[0];d=sex
    xmin=float(d.get('xmin'));  xmax=float(d.get('xmax'))
    bboxes['sex']=(xmin,xmax)

  #desc
  desc=[i for i in hblocks if i.text.strip().startswith('Desc')]
  if not desc: desc=[i for i in hwords if i.text.strip().startswith('Desc')]
  if not desc:
    print 'could not find block for description'
    return
  else:
    desc=desc[0];d=desc
    xmin=float(d.get('xmin'));  xmax=float(d.get('xmax'))
    bboxes['desc']=(xmin,xmax)

  #symp
  symp=[i for i in hblocks if i.text.strip().startswith('Sympt')]
  if not symp: symp=[i for i in hwords if i.text.strip().startswith('Sympt')]
  if not symp:
    print 'could not find block for symptoms'
    return
  else:
    symp=symp[0];d=symp
    xmin=float(d.get('xmin'));  xmax=float(d.get('xmax'))
    bboxes['symp']=(xmin,xmax)

  #comorb
  comorb=[i for i in hblocks if i.text.strip().startswith('Co-')]
  if not comorb: comorb=[i for i in hwords if i.text.strip().startswith('Co-')]
  if not comorb:
    print 'could not find block for comorb'
    return
  else:
    comorb=comorb[0];d=comorb
    xmin=float(d.get('xmin'));  xmax=float(d.get('xmax'))
    bboxes['comorb']=(xmin,xmax)

  #doa
  doa=[i for i in hblocks if i.text.strip().startswith('DOA')]
  if not doa: doa=[i for i in hwords if i.text.strip().startswith('DOA')]
  if not doa:
    print 'could not find block for DOA'
    return
  else:
    doa=doa[0];d=doa
    xmin=float(d.get('xmin'));  xmax=float(d.get('xmax'))
    bboxes['doa']=(xmin,xmax)

  #dod
  dod=[i for i in hblocks if i.text.strip().startswith('DOD')]
  if not dod:  dod=[i for i in hwords if i.text.strip().startswith('DOD')]
  if not dod:
    print 'could not find block for DOD'
    return
  else:
    dod=dod[0];d=dod
    xmin=float(d.get('xmin'));  xmax=float(d.get('xmax'))
    bboxes['dod']=(xmin,xmax)

  #place
  place=[i for i in hblocks if i.text.strip().startswith('Place')]
  if not place: place=[i for i in hwords if i.text.strip().startswith('Place')]
  if not place:
    if debug: print 'could not find block for place of deaths'
    
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
    print 'bbox of symp '+str(bboxes['symp'])+' and comorb: '+str(bboxes['comorb'])
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
      print '%s was not a valid entry' %(debug_clip)
      return
    x=str(margins[debug_clip][0])
    w=str(margins[debug_clip][1])
    cmd='pdftotext -x '+x+'  -W '+w+' -y 0 -H 1000  -nopgbrk -layout -f '+str(page_range[0])+' -l '+str(page_range[1])+' '+bulletin+' tmp.txt'
    print cmd
    os.system(cmd)
    print 'created debug clip in tmp.txt of '+debug_clip
  return margins

def helper_map_district_start_char_to_fullname(startchars=''):
  for k in karnataka_districts_map:
    if startchars.lower().startswith(k):
      return karnataka_districts_map[k]
def helper_correlate_signals(x,y,plot=False):
  if len(x)!=len(y):
    print 'array length %d %d are not same' %(len(x),len(y))
  # ~ corr=numpy.correlate(x-numpy.mean(x),y-numpy.mean(y),mode='full')
  corr=numpy.correlate(x,y,mode='full')
  lag = corr.argmax()-(len(x)- 1)
  if plot:
    import pylab
    pylab.plot(corr)
  print 'best lag between signals: '+str(lag)
  return corr
  
def helper_plot_linear_fit(x,y,label='',color=''):
  import pylab
  xr=numpy.arange(len(x))
  # ~ coef=numpy.polyfit(xr,y,1)
  coef=numpy.polyfit(x,y,1)
  poly1d_fn=numpy.poly1d(coef)
  # ~ pylab.plot(x,y, 'yo', x, poly1d_fn(x), '--k',label='Best linear fit')
  # ~ pylab.plot_date(x,poly1d_fn(xr), 'g',label='Best linear fit')
  if not color:    color='g'
  if not label:    label='Best linear fit'
  
  pylab.plot_date(x,poly1d_fn(x),color,label=label)

def helper_plot_exponential_fit(x,y,label='',color=''):
  import pylab  
  coef=numpy.polyfit(x,numpy.log(y),1)
  poly1d_fn=numpy.poly1d(coef)
  # ~ pylab.plot(x,y, 'yo', x, poly1d_fn(x), '--k',label='Best linear fit')
  # ~ pylab.plot_date(x,poly1d_fn(xr), 'g',label='Best linear fit')
  if not color:    color='r'
  if not label:    label='Best Exponential fit'
  
  pylab.plot(x,numpy.exp(poly1d_fn(x)),color,label=label)
  
  
def helper_get_mean_timeseries(recoveries):
  d1=datetime.date(2020,7,14);d2=datetime.date(2020,9,10);delta=d2-d1
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
      print 'no recovery info for '+str(dd)
      continue
    m1=0;m2=0
    if r1: m1=numpy.mean(r1)
    if r2: m2=numpy.mean(r2)
    # ~ mean_values.append((dd,numpy.mean(r),numpy.mean(r1),numpy.mean(r2)))
    mean_values.append((dd,numpy.mean(r),m1,m2))
    # ~ mean_values.append((dd,numpy.median(r),numpy.median(r1),numpy.median(r2)))
  return mean_values

def karnataka_read_csv():
  import csv;info=[]
  r=csv.reader(open('karnataka_fatalities_details_jul16_sep10.csv'))
  for i in r: info.append(i);
  info=info[1:];fatalities=[]
  for row in info[2:]:
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
  return fatalities
def helper_get_mean_deaths(deaths,filter_type='',date_type='',moving_average=True,ma_size=3,state='Tamil Nadu'):
  d1=datetime.date(2020,6,1);d2=datetime.date(2020,9,11);delta=d2-d1
  datetimes=[(d1 + datetime.timedelta(days=i)) for i in range(delta.days + 1)]
  datetimes=[datetime.datetime.combine(i,datetime.time(0, 0)) for i in datetimes]

  mean_values=[];capital='bengaluru'
  
  ma_delta=datetime.timedelta(days=ma_size)
  if state=='Tamil Nadu':capital='chennai'
  elif state=='Kerala':capital='Thiruvananthapuram'

  for dd in datetimes:
    d='';d1='';d2=''
    if moving_average:
      if not date_type or date_type=='death': #default behavious
        d=[i for i in deaths if i.date_of_death<=(dd+ma_delta) and i.date_of_death>=(dd-ma_delta)]
        d1=[i for i in deaths if i.date_of_death<=(dd+ma_delta) and i.date_of_death>=(dd-ma_delta) and i.district==capital]
        d2=[i for i in deaths if i.date_of_death<=(dd+ma_delta) and i.date_of_death>=(dd-ma_delta) and i.district!=capital]
      elif date_type=='reporting':
        d=[i for i in deaths if i.date_of_reporting and i.date_of_reporting<=(dd+ma_delta) and i.date_of_reporting>=(dd-ma_delta)]
        d1=[i for i in deaths if i.date_of_reporting and i.date_of_reporting<=(dd+ma_delta) and i.date_of_reporting>=(dd-ma_delta) and i.district==capital]
        d2=[i for i in deaths if i.date_of_reporting and i.date_of_reporting<=(dd+ma_delta) and i.date_of_reporting>=(dd-ma_delta) and i.district!=capital]
      elif date_type=='admission':
        d=[i for i in deaths if i.date_of_admission<=(dd+ma_delta) and i.date_of_admission>=(dd-ma_delta)]
        d1=[i for i in deaths if i.date_of_admission<=(dd+ma_delta) and i.date_of_admission>=(dd-ma_delta) and i.district==capital]
        d2=[i for i in deaths if i.date_of_admission<=(dd+ma_delta) and i.date_of_admission>=(dd-ma_delta) and i.district!=capital]
  
    else:
      d=[i for i in deaths if i.date_of_death==dd]
      d1=[i for i in deaths if i.date_of_death==dd and i.district==capital]
      d2=[i for i in deaths if i.date_of_death==dd and i.district!=capital]
  
    m1=0;m2=0
    
    if filter_type=='gender': #find fraction of males in daily deaths on date
      if d: d=100*float(len([i for i in d if i.gender=='M']))/len(d)
      else: d=0
      if d1: d1=100*float(len([i for i in d1 if i.gender=='M']))/len(d1)
      else: d1=0
      if d2: d2=100*float(len([i for i in d2 if i.gender=='M']))/len(d2)
      else: d2=0
    elif filter_type=='origin': #find fraction of SARI/ILI in daily deaths on date
      d=100*float(len([i for i in d if i.origin in ['SARI','ILI']]))/len(d)
      d1=100*float(len([i for i in d1 if i.origin in ['SARI','ILI']]))/len(d1)
      d2=100*float(len([i for i in d2 if i.origin in ['SARI','ILI']]))/len(d2)
    elif filter_type=='comorb': #find fraction of SARI/ILI in daily deaths on date
      d=100*float(len([i for i in d if i.comorbidities!=['']]))/len(d)
      d1=100*float(len([i for i in d1 if i.comorbidities!=['']]))/len(d1)
      d2=100*float(len([i for i in d2 if i.comorbidities!=['']]))/len(d2)
    elif filter_type=='admission_death': #find fraction of SARI/ILI in daily deaths on date
      d=[i.admission_death_interval for i in d if i.admission_death_interval>=0]
      d1=[i.admission_death_interval for i in d1 if i.admission_death_interval>=0]
      d2=[i.admission_death_interval for i in d2 if i.admission_death_interval>=0]
    elif filter_type=='death_reporting': #find fraction of SARI/ILI in daily deaths on date
      d=[i.death_reporting_interval for i in d if i.death_reporting_interval]
      d1=[i.death_reporting_interval for i in d1 if i.death_reporting_interval and i.death_reporting_interval>=0]
      d2=[i.death_reporting_interval for i in d2 if i.death_reporting_interval and i.death_reporting_interval>=0]
    elif filter_type=='raw_number': #find fraction of SARI/ILI in daily deaths on date
      if moving_average:
        d=float(len(d))/(2*ma_size+1)
        d1=float(len(d1))/(2*ma_size+1)
        d2=float(len(d2))/(2*ma_size+1)
      else:
        d=float(len(d))
        d1=float(len(d1))
        d2=float(len(d2))
    else: #find all ages on date
      d=[i.age for i in d]
      d1=[i.age for i in d1]
      d2=[i.age for i in d2]

    if filter_type in ['gender','origin','comorb','raw_number']: #find percent of males in daily deaths over time
      mean_values.append((dd,d,d1,d2))
    else:
      if not d:
        # ~ print 'no deaths info for '+str(dd)
        continue
      m=0;m1=0;m2=0
      if d1: m1=numpy.mean(d1)
      if d2: m2=numpy.mean(d2)
      if d: m=numpy.mean(d)
      mean_values.append((dd,m,m1,m2))
  return mean_values

def kerala_parse_deaths(bulletin='',format_type='new'):  
  b=[i.strip() for i in open('olddeaths.txt').readlines() if i.strip()][3:]
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

  for pdf in pdfs:
    print 'parsing '+pdf
    cmd='pdftotext -nopgbrk -layout "'+pdf+'" tmp.txt';os.system(cmd)
  
    b=[i.strip() for i in open('tmp.txt').readlines() if i.strip()][3:]
    bulletin_date=[i for i in b if i.startswith('Date:')]
    if not bulletin_date:
      print 'could not find date from bulletin: '+bulletin+' !!'
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
      print 'could not find Total cases and iunk in bulletin: '+bulletin
      return

    comm.append(kerala_community_tr(bulletin_date,percent_unknown_origin))

    #death details
    entries=[i for i in death_details if i.strip()[0].isdigit()]
    for entry in entries:
      if len(entry.split())==1: continue #empty row
      try:
        district=entry.split()[1].strip()
      except:
        print 'error getting district with enrty: '+entry
        return
  
      age=entry.split()[2].strip()
      if 'month' in entry.split()[3].lower(): age='1'
  
      gender=entry.split()[-3].strip()
      if gender.lower()=='female': gender='F'
      else: gender='M'
  
      dod=entry.split()[-2].strip().replace('.','/').replace('-','/')
      if dod.count('/')==2:
        if dod.endswith('/20'):dod+='20'
        dod=datetime.datetime.strptime(dod,'%d/%m/%Y')
  
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
  
  
def karnataka_parse_deaths(bulletin='09_09_2020.pdf',bulletin_date=datetime.datetime(2020, 9, 9, 0, 0),page_range='',stop_debug=''):
  if stop_debug and (not page_range): #means coming from debug
    (bulletin_date,annex_range)=karnataka_bulletin_parser(bulletin,return_date_only=True)
    page_range=annex_range['deaths']
    
  start_page=str(page_range[0])
  end_page=str(page_range[1])

  margins=karnataka_bulletin_get_margins(bulletin,page_range)
  if not margins and stop_debug:
    print 'no margins found with page_range: '+str(page_range)

  format_type=1;#means place column exists
  if 'place' not in margins: format_type=0;#place colum does not exist

  #get districts name
  districts=[]
  x=str(margins['district'][0]);w=str(margins['district'][1]); #for new
  cmd='pdftotext -x '+x+'  -W '+w+' -y 0 -H 1000  -nopgbrk -layout -f '+start_page+' -l '+end_page+' '+bulletin+' tmp.txt';os.system(cmd);
  b=[i.strip() for i in open('tmp.txt').readlines() if i.strip().lower().startswith(tuple(karnataka_districts_map.keys()))]

  districts=[helper_map_district_start_char_to_fullname(i) for i in b]

  if stop_debug=='district':
    print 'stopping after getting district info'
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
        print 'when parsing origin, field in b was less than 4 for: '+i+' last_entr: '+last_entry
        
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
    print 'stopping after getting origin info'
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
    print 'stopping after getting comorb info'
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
          print 'backtrack to -'+str(lindex)+' in '+i.strip()+' last_term: '+last_term; #+' ,start_char_idx: '+str(start_char_idx)
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
            if stop_debug=='doadod1': print '\tcorrected to: '+highlight(b[j])
          else:
            b[j-1]+='  '+last_term.replace('at','').strip()
            b[j-1]=b[j-1].replace('\n','').replace('_','').strip()
            if stop_debug=='doadod1': print '\tcorrected to: '+highlight(b[j-1])
            
  
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
    print 'stopping at beginning of doadod proc'
    return districts,patient_numbers,ages,genders,origins,comorbidities,b

  
    
  dates_of_admission=[];dates_of_death=[]
  for i in b:
    #correct for malformed bulletins
    i=i.replace('-202020','-2020').replace('-20020','-2020').replace('-2020s','-2020').replace('at','').strip(); 
    i=i.replace('-072020','-07-2020').replace('-082020','-08-2020').replace('-092020','-09-2020').replace('-2002','-2020')
    i=i.replace('23- 08-2020','23-08-2020')
    
    if 'rought' in i:
      if stop_debug=='doadod':
        print 'parsing single line "rought" string in '+i
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
          print 'got unusual date string: %s when converting to date_of_admission, i: %s' %(ll,i)
          date_of_admission=datetime_doa_marker
        ll=l[1].replace('at','').strip()
        if '-2020' not in ll:
          if '-200' in ll: ll=ll[:-1]+'20'
          elif '-20' in ll:ll+='20'
          elif ll.endswith('-'):ll+='2020'
        try:
          date_of_death=datetime.datetime.strptime(ll,'%d-%m-%Y')
        except ValueError:
          print 'got unusual date string: %s when converting to date_of_death, i: %s' %(ll,i)
          date_of_death=datetime_doa_marker
    dates_of_admission.append(date_of_admission)
    dates_of_death.append(date_of_death)

  if stop_debug=='doadod': #prelim
    print 'stopping at end of doadod proc'
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
      print '---'
      print 'districts',len(districts)
      print 'patient_numbers',len(patient_numbers)
      print 'ages',len(ages)
      print 'genders',len(genders)
      print 'origins',len(origins)
      print 'comorbidities',len(comorbidities)
      print 'dates_of_admission',len(dates_of_admission)
      print 'dates_of_death',len(dates_of_death)
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
      print 'error in getting icu usage with line: %s and bulletin_date ' %(i)+str(bulletin_date)
    
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
      print 'error parsing line '+line+' in bulletin: '+bulletin
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
      print 'error parsing district in line: %s in bulletin: %s' %(line,bulletin)
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
      print 'error parsing age: %s in line: %s in bulletin: %s' %(age,line,bulletin)
      return
    if not pno.isdigit():
      print 'error parsing pno: %s in line: %s in bulletin: %s' %(pno,line,bulletin)
      return
    if not history:
      print 'error parsing history in line: %s in bulletin: %s' %(line,bulletin)
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
    print '%s does not exist. Please give pdf bulletin file as input' %(bulletin)
    return -1
  cmd='pdftotextx -nopgbrk -layout -table "'+bulletin+'" tmp.txt';os.system(cmd);
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
  # ~ if return_date_only:    return bulletin_date

  #find pages for Annexure 1(discharges),2(deaths),3(icu_usage)
  annexures=[i for i in b if 'nnexure' in i]
  annexures_indices=[b.index(i) for i in annexures]

  discharge_annex_range=[];deaths_annex_range=[];icu_annex_range=[];
  annex_range=[];lastpage=0

  #HACKS FOR MISFORMED BULLETINS
  misformed_bulletins=['08_05_2020.pdf','08_07_2020.pdf','07_18_2020.pdf']
      
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
        print '"page n/n" info not found for %s with page_string: %s' %(b[annexure_index],page_string)

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
    deaths=karnataka_parse_deaths(bulletin,bulletin_date,annex_range['deaths'])

 
  
  if return_specific:
    if return_specific=='icu':
      return icu_usage
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
        print 'crashed in '+entry
        return
      icu=int(icu);
      icu_obj=generic_icu_usage(bulletin_date,district,icu,state='Karnataka');all_icu.append(icu_obj)
  #last
  chunk=b[indices[-1]+1:]
  for entry in chunk:
    district=entry.split(':')[0].strip()
    try:
      icu=entry.split(':')[1].strip();icu=int(icu);
    except:
      print 'crashed in '+entry
      return
    icu_obj=generic_icu_usage(bulletin_date,district,icu,state='Karnataka');all_icu.append(icu_obj)
  return all_icu

def karnataka_parser(return_specific=''):
  bulletin_pdfs=[i for i in os.listdir('.') if i.endswith('.pdf')]
  bulletin_pdfs.sort()
  all_discharges=[];all_icu_usage=[];all_deaths=[]
  if return_specific=='icu': #directly parse txt clipping of icu usage
    all_icu_usage=karnataka_parse_icu_clipping()
  for bulletin_pdf in bulletin_pdfs:
    print 'parsing bulletin %s' %(bulletin_pdf)    
    try:
      if return_specific:
        pass
      else:
        (discharges,icu_usage,deaths)=karnataka_bulletin_parser(bulletin_pdf)
        all_discharges.extend(discharges)
        all_icu_usage.extend(icu_usage)
        all_deaths.extend(deaths)
    except:
      print 'parsing failed for :%s' %(bulletin_pdf)
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
def get_antigen_tests(state='Karnataka',verbose=False):
  x=json.load(open('state_test_data.json'))
  x=[i for i in x['states_tested_data'] if i.has_key('antigentests') and i['antigentests'] and i['state']==state]

  antigen_on_day=0;tests_on_day=0;percent_antigen=0
  all_antigen=[]
  
  for idx in range(1,len(x)):
    i=x[idx]
    date=i['updatedon']
    datetime_i=datetime.datetime.strptime(i['updatedon'],'%d/%m/%Y')
    
    tests_on_day=int(i['totaltested'])-int(x[idx-1]['totaltested'])
    antigen_on_day=int(i['antigentests'])-int(x[idx-1]['antigentests'])
    percent_antigen=100*(float(antigen_on_day)/tests_on_day)
    all_antigen.append((date,tests_on_day,antigen_on_day,percent_antigen))
  
  if verbose:
    print 'For state: %s' %(state)
    for i in all_antigen:
      (date,tests_on_day,antigen_on_day,percent_antigen)=i
      print '%s: %d tests,  %.1f percent (%d tests) were antigen' %(date,tests_on_day,percent_antigen,antigen_on_day)
  return all_antigen

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
  x=json.load(open('state_test_data.json'))
  all_icu_data=[i for i in x['states_tested_data'] if i['peopleinicu'] and i['state']==state]
  if not all_icu_data:
    print 'State: %s does not have any data on ICU usage (as per covid19indiadotorg API)' %(state)
    return 

  all_percent_icu=[]
  for entry in all_icu_data:
    icu_usage=int(entry['peopleinicu'])
    date_of_entry=entry['updatedon']
    actives_on_this_date=get_cases(state,date_of_entry,case_type='active')
    percent_icu=100*(float(icu_usage)/actives_on_this_date)
    all_percent_icu.append((date_of_entry,percent_icu,icu_usage))

  if verbose:
    print 'For state: %s, the variation of pecent of patients in ICU is ..' %(state)
    for i in all_percent_icu:
      print '%s : %.3f (%d in icu)' %(i[0],i[1],i[2])
  return all_percent_icu

def estimate_lag():
  states=['Haryana',]
  for state in states:
    d=get_cases(state=states,case_type='deaths',return_full_series=True)

def state_demographics(state='Punjab'):
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
  x=json.load(open('state_test_data.json'))
  all_ventilator_data=[i for i in x['states_tested_data'] if i['peopleonventilators'] and i['state']==state]
  if not all_ventilator_data:
    print 'State: %s does not have any data on ventilator usage (as per covid19indiadotorg API)' %(state)
    return 

  all_percent_ventilator=[]
  for entry in all_ventilator_data:
    ventilator_usage=int(entry['peopleonventilators'])
    date_of_entry=entry['updatedon']
    actives_on_this_date=get_cases(state,date_of_entry,case_type='active')
    percent_ventilator=100*(float(ventilator_usage)/actives_on_this_date)
    all_percent_ventilator.append((date_of_entry,percent_ventilator,ventilator_usage))

  if verbose:
    print 'For state: %s, the variation of pecent of patients on ventilator is ..' %(state)
    for i in all_percent_ventilator:
      print '%s : %.3f (%d on ventilator)' %(i[0],i[1],i[2])
  return all_percent_ventilator

def make_plots(use_all_states=False,use_solid_lines=False):
  import pylab
  states_icu=['Punjab','Haryana','Kerala','Telangana','Karnataka']
  states_ventilator=['Punjab','Haryana','Kerala','Telangana','Gujarat']
  # ~ states_icu=['Telangana']
  # ~ states_ventilator=['Telangana']

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
  pylab.show(); pylab.close();
  figure = pylab.gcf();figure.set_size_inches(8, 6);pylab.savefig('ICU_usage.png', dpi = 100);
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
  pylab.show(); pylab.close()
  figure = pylab.gcf();figure.set_size_inches(8, 6);pylab.savefig('Ventilator_usage.png', dpi = 100);



    
if __name__=='__main__':
  make_plots()
