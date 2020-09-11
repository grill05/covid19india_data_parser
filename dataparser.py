#!/usr/bin/python2

#code runs with python-2 (for python-3, just convert the "print" statements to function
#to install dependencies "pip install pylab json requests"

# ~ for moving average with window 'N'
# ~ np.convolve(x, np.ones((N,))/N, mode='valid')

import os,sys
import json,datetime,numpy,requests
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
global_karnataka_case_series=''
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

  
def update_data_files():
  urls=['https://api.covid19india.org/states_daily.json','https://api.covid19india.org/data.json','https://api.covid19india.org/state_test_data.json']
  for i in urls:
    filename=os.path.split(i)[1]
    if os.path.exists(filename):
      os.remove(filename)
    cmd='wget -q "'+i+'" -O "'+filename+'"';
    print cmd
    os.system(cmd);
      
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
        print 'for %s, could not distrct: %s from ss: %s' %(fatality_string,district,ss)
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

class karnataka_fatality():
  district='';patient_number='';age='';gender='';origin='';comorbidities='';
  date_of_detection='';date_of_admission='';date_of_death='';hospital_type=''
  date_of_reporting=''
  detection_admission_interval=''
  detection_death_interval=''
  admission_death_interval=''
  death_reporting_interval=''
  def __init__(self,district,patient_number,age,gender,origin,comorbidity,date_of_admission,date_of_death,hospital_type,bulletin_date):
    self.district=district
    self.patient_number=int(patient_number.replace('n',''))
    self.age=int(age)
    self.gender=gender
    self.origin=origin
    self.comorbidities=comorbidity.split(',')
    self.date_of_detection=karnataka_map_patient_no_to_date(self.patient_number,global_karnataka_case_series)
    
    self.date_of_admission=date_of_admission
    self.date_of_death=date_of_death
    self.date_of_reporting=bulletin_date
    # ~ print self.date_of_reporting
    
    self.hospital_type=hospital_type

    if self.date_of_admission==datetime_doa_marker: #means patient was dead on arrival
      self.admission_death_interval=-1
      if self.date_of_detection:
        self.detection_admission_interval=(self.date_of_death-self.date_of_detection).days    
    else:
      self.admission_death_interval=(self.date_of_death-self.date_of_admission).days
      if self.date_of_detection:
        self.detection_admission_interval=(self.date_of_admission-self.date_of_detection).days    
    if self.date_of_detection:
      self.detection_death_interval=(self.date_of_death-self.date_of_detection).days
    self.death_reporting_interval=(self.date_of_reporting-self.date_of_death).days
      
  def info(self):
    info_str='P.no %d District: %s Age: %d Gender: %s Origin: %s\n' %(self.patient_number,self.district,self.age,self.gender,self.origin)
    info_str+='Comorbidities: %s\n' %(' '.join(self.comorbidities))
    dod='N/A'
    if self.date_of_detection:
      dod=self.date_of_detection.strftime('%d/%m/%Y')
    info_str+='Detected: %s Admitted: %s Died: %s\n' %(dod,self.date_of_admission.strftime('%d/%m/%Y'),self.date_of_death.strftime('%d/%m/%Y'))
    info_str+='admission_death_interval: %d\n' %(self.admission_death_interval)
    if self.detection_admission_interval: info_str+='detection_admission_interval: %d\n' %(self.detection_admission_interval)    
    if self.detection_death_interval: info_str+='detection_death_interval: %d\n' %(self.detection_death_interval)
    info_str+='death_reporting_interval: %d' %(self.death_reporting_interval)
    print info_str.strip()
    
class karnataka_icu_usage():
  date='';district='';icu_usage=''
  def __init__(self,bulletin_date,district_name,icu_usage):
    self.date=bulletin_date
    self.district=district_name
    self.icu_usage=icu_usage
  def info(self):
    info_str='In district: %s on %s, icu_usage: %d' %(self.district,self.date.strftime('%d-%m-%Y'),self.icu_usage)
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


def list_value_frequency(l=[]): #make frequency distribution of list't values
  values=list(set(l));values.sort()
  d={};freq=[]
  for i in l:
    if i in d: d[i]+=1
    else: d[i]=1
  freq.extend([100*(d[i]/float(len(l))) for i in values])
  return (values,freq)
  
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

def karnataka_map_patient_no_to_date(patient_no=1,case_series=[]):
  date_of_case=''

  #need this for function that calculates which date a P. no. falls on
  if not case_series:
    case_series=get_cases(state='Karnataka',case_type='confirmed',return_full_series=True,verbose=False)
    
  for i in case_series:
    if patient_no>i[1]: continue
    else:               date_of_case=i[0];break;
  return date_of_case

def karnataka_bulletin_get_margins(bulletin='09_09_2020.pdf',page_range=(19,23)):
  cmd='pdftotext -x 0 -y 0 -W 1000 -H 200 -bbox-layout -nopgbrk -layout -f '+str(page_range[0])+' -l '+str(page_range[1])+' "'+bulletin+'" tmp.txt';os.system(cmd)
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

  #s.no
  sno=[i for i in hblocks if i.text.strip().startswith('Sl.')]
  if not so:
    print 'could not find block for serial number'
    return
  sno=sno[0];d=sno
  xmin=float(d.get('xmin'));  xmax=float(d.get('xmax'))

  #district
  district=[i for i in hblocks if i.text.strip().startswith('District')]
  if not district:
    print 'could not find block for district'
    return
  district=district[0];d=district
  xmin=float(d.get('xmin'));  xmax=float(d.get('xmax'))

  #State P No
  spno=[i for i in hblocks if i.text.strip().startswith('State')]
  if not spno:
    print 'could not find block for State P. no'
    return
  spno=spno[0];d=spno
  xmin=float(d.get('xmin'));  xmax=float(d.get('xmax'))

  #age
  age=[i for i in hblocks if i.text.strip().startswith('Age')]
  if not age:
    print 'could not find block for Age'
    return
  age=age[0];d=age
  xmin=float(d.get('xmin'));  xmax=float(d.get('xmax'))

  #sex
  sex=[i for i in hblocks if i.text.strip().startswith('Sex')]
  if not sex:
    print 'could not find block for sex'
    return
  sex=sex[0];d=sex
  xmin=float(d.get('xmin'));  xmax=float(d.get('xmax'))

  #desc
  desc=[i for i in hblocks if i.text.strip().startswith('Desc')]
  if not desc:
    print 'could not find block for description'
    return
  desc=desc[0];d=desc
  xmin=float(d.get('xmin'));  xmax=float(d.get('xmax'))

  #symp
  symp=[i for i in hblocks if i.text.strip().startswith('Sympt')]
  if not symp:
    print 'could not find block for symptoms'
    return
  symp=symp[0];d=symp
  xmin=float(d.get('xmin'));  xmax=float(d.get('xmax'))

  #comorb
  comorb=[i for i in hblocks if i.text.strip().startswith('Co')]
  if not comorb:
    print 'could not find block for comorb'
    return
  comorb=comorb[0];d=comorb
  xmin=float(d.get('xmin'));  xmax=float(d.get('xmax'))

  #doa
  doa=[i for i in hblocks if i.text.strip().startswith('DOA')]
  if not doa:
    print 'could not find block for DOA'
    return
  doa=doa[0];d=doa
  xmin=float(d.get('xmin'));  xmax=float(d.get('xmax'))

  #dod
  dod=[i for i in hblocks if i.text.strip().startswith('DOD')]
  if not dod:
    print 'could not find block for DOD'
    return
  dod=dod[0];d=dod
  xmin=float(d.get('xmin'));  xmax=float(d.get('xmax'))

  #place
  place=[i for i in hblocks if i.text.strip().startswith('Place')]
  if not place:
    print 'could not find block for place of deaths'
    return
  place=place[0];d=place
  xmin=float(d.get('xmin'));  xmax=float(d.get('xmax'))


  
def karnataka_parse_deaths(bulletin='09_09_2020.pdf',bulletin_date=datetime.datetime(2020, 9, 9, 0, 0),page_range=(19,23)):
  start_page=str(page_range[0])
  end_page=str(page_range[1])

  format_type='new'

  #first find format (end with DOD or place also)
  cmd='pdftotextx  -margint 10 -marginb 700 -nopgbrk -layout -table -f '+start_page+' -l '+end_page+' '+bulletin+' tmp.txt';os.system(cmd);
  b=[i.strip() for i in open('tmp.txt').readlines() if i.strip() if 'DOD' in i]
  b=b[0]
  if b.endswith('DOD'): format_type='old'

  #get districts name
  districts=[]
  left=10;right=500; #for new
  cmd='pdftotextx -marginl '+str(left)+' -marginr  '+str(right)+'  -margint 10 -marginb 40 -nopgbrk -layout -table -f '+start_page+' -l '+end_page+' '+bulletin+' tmp.txt';os.system(cmd);
  b=[i.strip() for i in open('tmp.txt').readlines() if i.strip()]

  d=''
  for j in range(len(b)):
    i=b[j]
    if i[0].isdigit():      
      d=''.join(i.split()[1:]).strip()
      if j<(len(b)-1) and not b[j+1][0].isdigit(): #split name
        d+=b[j+1].strip()
      districts.append(d)

  #p.no,gender,age,origin
  left=115;right=340
  if format_type=='old': right=320
  cmd='pdftotextx -marginl '+str(left)+' -marginr  '+str(right)+'  -margint 10 -marginb 40 -nopgbrk -layout -table -f '+start_page+' -l '+end_page+' '+bulletin+' tmp.txt';os.system(cmd);
  b=[i.strip() for i in open('tmp.txt').readlines() if i.strip() and i.strip()[0].isdigit()]

  patient_numbers=[];ages=[];genders=[];origins=[]
  for i in b:
    if len(i.split())<4: continue; #need all fields
    patient_number=i.split()[0]
    age=i.split()[1]
    gender=i.split()[2]
    origin=i.split()[3]
    if 'under' in origin or 'contact' in origin or 'trac' in origin: origin='CONT'
    patient_numbers.append(patient_number);ages.append(age);genders.append(gender);origins.append(origin)


  #comorbidities
  left=340;right=210
  if format_type=='old': left=370;right=170
  cmd='pdftotextx -marginl '+str(left)+' -marginr  '+str(right)+'  -margint 10 -marginb 40 -nopgbrk -layout -table -f '+start_page+' -l '+end_page+' '+bulletin+' tmp.txt';os.system(cmd);
  b=[i.strip() for i in open('tmp.txt').readlines() if i.strip() and (i.strip()=='-' or i.strip()[0].isupper())]
  comorbidities=[];comorbidity=''
  for i in b:
    # ~ print i
    if i=='-':
      comorbidities.append('NONE')
      comorbidity=''
    elif i.endswith(','):
      comorbidity+=i
    else:
      comorbidity+=i
      comorbidities.append(comorbidity)
      comorbidity=''      

  #DOA,DOD
  left=385;right=110
  cmd='pdftotextx -marginl '+str(left)+' -marginr  '+str(right)+'  -margint 10 -marginb 40 -nopgbrk -layout -table -f '+start_page+' -l '+end_page+' '+bulletin+' tmp.txt';os.system(cmd);
  b=[i.strip() for i in open('tmp.txt').readlines() if i.strip() and (i.strip()[0].isdigit() and '-' in i) ]

  dates_of_admission=[];dates_of_death=[]
  for i in b:

      
    l=i.split()
    if len(l)==1: #brought dead on date
      date_of_admission=datetime_doa_marker; #use 1 jan as marker
      ll=l[0]
      if '-2020' not in ll and '-20' in ll:ll+='20'
      date_of_death=datetime.datetime.strptime(ll,'%d-%m-%Y')
    else:
      date_of_admission=datetime.datetime.strptime(l[0],'%d-%m-%Y')
      ll=l[1]
      if '-2020' not in ll and '-20' in ll:ll+='20'
      date_of_death=datetime.datetime.strptime(ll,'%d-%m-%Y')
    dates_of_admission.append(date_of_admission)
    dates_of_death.append(date_of_death)

  cmd='pdftotextx -marginl 500 -marginr 20 -margint 10 -marginb 40 -nopgbrk -layout -table -f '+start_page+' -l '+end_page+' '+bulletin+' tmp.txt';os.system(cmd);
  b=[i.strip() for i in open('tmp.txt').readlines() if i.strip() if ('private' in i.strip().lower() or 'designated' in i.strip().lower())]

  hospital_types=[]
  for i in b:    hospital_types.append(i.lower())

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
      hospital_type=''
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

    fatality=karnataka_fatality(district,patient_number,age,gender,origin,comorbidity,date_of_admission,date_of_death,hospital_type,bulletin_date)
    fatalities.append(fatality)
      
  return fatalities
      
  
  
def karnataka_parse_icu_usage(bulletin_date=datetime.datetime(2020, 9, 9, 0, 0)):
  b=[i.strip() for i in open('tmp.txt').readlines() if i.strip() and i.strip()[0].isdigit()]
  all_icu_obj=[]
  for i in b:
    district_name=''.join(i.split()[1:-1])
    icu_usage=i.split()[-1]
    assert(icu_usage.isdigit())
    icu_usage=int(icu_usage)
    icu_obj=karnataka_icu_usage(bulletin_date,district_name,icu_usage)
    all_icu_obj.append(icu_obj)
  return all_icu_obj

  
def karnataka_parse_discharges(bulletin_date=datetime.datetime(2020, 9, 9, 0, 0)):
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
      if not patient_number.replace('n','').replace(',','').isdigit(): continue #p.no must be digit
      dd=karnataka_discharge(district_name,patient_number,bulletin_date)
      if dd.district!='ERROR':      all_dischages_objects.append(dd)

  return all_dischages_objects
        



def karnataka_bulletin_parser(bulletin='',return_date_only=False):
  if not os.path.exists(bulletin):
    print '%s does not exist. Please give pdf bulletin file as input' %(bulletin)
    return -1
  cmd='pdftotextx -nopgbrk -layout -table "'+bulletin+'" tmp.txt';os.system(cmd);
  b=[i.strip() for i in open('tmp.txt').readlines() if i.strip()]

  #find date of bulletin
  date_string='';bulletin_date=''
  for i in b:
    i=i.lower()
    if i.startswith('date:'):
      date_string=i.split(':')[1].strip().replace('202020','2020')
      bulletin_date=datetime.datetime.strptime(date_string,'%d-%m-%Y')
      break
  # ~ if return_date_only:    return bulletin_date

  #find pages for Annexure 1(discharges),2(deaths),3(icu_usage)
  annexures=[i for i in b if 'nnexure' in i]
  annexures_indices=[b.index(i) for i in annexures]

  discharge_annex_range=[];deaths_annex_range=[];icu_annex_range=[];
  annex_range=[];lastpage=0
  
  for annexure_index in annexures_indices:
    pagenum=0
    
    page_string=b[annexure_index-1].lower()
    if 'page' in page_string:
      pagenum=page_string.split('page')[1].strip().split('of')[0].strip()
      lastpage=page_string.split('page')[1].strip().split('of')[1].strip()
      assert(pagenum.isdigit());assert(lastpage.isdigit())
      pagenum=int(pagenum)+1
      lastpage=int(lastpage)
    else:
      print '"page n/n" info not found for %s with page_string: %s' %(b[annexure_index],page_string)
    info_string=b[annexure_index+1].lower()
    if 'discharges' in info_string:
      annex_range.append(('discharges',pagenum))
    elif 'deaths' in info_string:
      annex_range.append(('deaths',pagenum))
    elif 'icu' in info_string:
      annex_range.append(('icu',pagenum))

  #convert to dict
  dc={}
  for i in range(len(annex_range)):
    if i<(len(annex_range)-1):
      dc[annex_range[i][0]]=(annex_range[i][1],annex_range[i+1][1]-1)
    else:
      dc[annex_range[i][0]]=(annex_range[i][1],annex_range[i][1])
  annex_range=dc

  if return_date_only:    return (bulletin_date,annex_range)
  #get discharges info

  cmd='pdftotextx -nopgbrk -layout -table -f '+str(annex_range['discharges'][0])+' -l '+str(annex_range['discharges'][1])+' '+bulletin+' tmp.txt';os.system(cmd);

  discharges=karnataka_parse_discharges(bulletin_date)

  #get icu info
  cmd='pdftotextx -nopgbrk -layout -table -f '+str(annex_range['icu'][0])+' -l '+str(annex_range['icu'][1])+' '+bulletin+' tmp.txt';os.system(cmd);
  icu_usage=karnataka_parse_icu_usage(bulletin_date)
  
  #get deaths info
  
  deaths=karnataka_parse_deaths(bulletin,bulletin_date,annex_range['deaths'])

 
  
  # ~ return bulletin_date,annex_range,discharges
  return (discharges,icu_usage,deaths)



def karnataka_parser():
  bulletin_pdfs=[i for i in os.listdir('.') if i.endswith('.pdf')]
  bulletin_pdfs.sort()
  all_discharges=[];all_icu_usage=[];all_deaths=[]
  for bulletin_pdf in bulletin_pdfs:
    print 'parsing bulletin %s' %(bulletin_pdf)    
    try:
      (discharges,icu_usage,deaths)=karnataka_bulletin_parser(bulletin_pdf)
      all_discharges.extend(discharges)
      all_icu_usage.extend(icu_usage)
      all_deaths.extend(deaths)
    except:
      print 'parsing failed for :%s' %(bulletin_pdf)    
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

#cache this to avoid repeated file reads
if os.path.exists('states_daily.json'):
  global_karnataka_case_series=get_cases(state='Karnataka',case_type='confirmed',return_full_series=True,verbose=False)

    
if __name__=='__main__':
  make_plots()
