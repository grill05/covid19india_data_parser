#!/usr/bin/python2

#code runs with python-2 (for python-3, just convert the "print" statements to function
#to install dependencies "pip install pylab json requests"

# ~ for moving average with window 'N'
# ~ np.convolve(x, np.ones((N,))/N, mode='valid')

import os,sys,copy,tqdm,csv
import json,datetime,numpy,requests,colorama,pylab
import matplotlib.dates as mdates
import numpy as np
datetime_doa_marker=datetime.datetime(2020, 1, 1, 0, 0)

TMPDIR='/storage/emulated/0/code/covid19india_data_parser/ims/tmp/'
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
                    "wb" : "West Bengal" ,
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

def parse_census(state='Tamil Nadu',metric='mean age'):
  if state=='Delhi':
    state='NCT of Delhi'
  r=csv.reader(open('census.csv'))
  info=[]
  for i in r: info.append(i)
  data=[i for i in info if i[0]==state]
#  print(len(data))
  if metric=='mean age':
    data=data[1:-3]#exclude last 2 rows and initial one
    agedict={}
    for i in data:
      age=int(i[1])
      num_persons=int(i[2])
      agedict[age]=num_persons
    tot_persons=sum(list(agedict.values()))
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

def get_cases_global(country='India',case_type='confirmed',do_moving_average=True):
    import csv
    fname='time_series_covid19_confirmed_global.csv'
    if case_type.startswith('deaths'): fname=fname.replace('confirmed','deaths')
    elif case_type.startswith('recovered'): fname=fname.replace('confirmed','recovered')
    r=csv.reader(open(fname))
    info=[]
    for i in r: info.append(i)
    dates=info[0][4:]
    dates=[datetime.datetime.strptime(d+'20','%m/%d/%Y') for d in dates]
    cdata=[i for i in info if i[1]==country]
    if not cdata: print('info for %s not found!' %(country));return
    cdata=np.int_(cdata[0][4:])
    if '_delta' in case_type:
        cdata=np.diff(cdata)
        cdata=np.append(np.array([0]),cdata)
    if do_moving_average:
      cdata=moving_average(cdata)

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
def get_mortality_rate(state='Tamil Nadu',district='',return_full_series=False,do_dpm=False,plot=False):
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
    dpm=(np.float64(d)/pop)
    x=list(zip(dates,m))

    if do_dpm: x=list(zip(dates,dpm))
    x=[i for i in x if i[0]>=datetime.datetime(2020,5,1,0,0)]
    dates,m=zip(*x)
    if plot:
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


def get_symptomatic(state='Telangana',asymp=False,plot=False):
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
      
def fix_faulty_json():
  b=[i for i in open('states_daily.json').readlines()]
  b[22165]=b[22165].replace('"0"','"135"')
  b[22294]=b[22294].replace('"0"','"113"')
  b[22423]=b[22423].replace('"0"','"104"')
  b[22552]=b[22552].replace('"0"','"116"')
  b[22681]=b[22681].replace('"0"','"128"')
  a=open('states_daily.json','w')
  for i in b: a.write(i)
  a.close()
##date must be given as 01/09/2020 for September 1,2020
##State must be fullname (see dict above)
def get_cases_district(state='Karnataka',district='Bengaluru Urban',date='01/09/2020',case_type='confirmed_delta',return_full_series=True,verbose=False):
  
  x=json.load(open('data-all.json'))
  d=list(x.keys());d.sort()
  dates=[datetime.datetime.strptime(i,'%Y-%m-%d') for i in d];
  state_code=state_name_to_code[state].upper()
  returned=[]

  first30=False
  if case_type=='first30deaths' : first30=True;case_type='deaths' 
  
  for date in d:
    dt=datetime.datetime.strptime(date,'%Y-%m-%d')
    if dt<=datetime.datetime(2020,4,1,0,0): continue
    if  not (state_code in x[date] and 'districts' in x[date][state_code]) : continue
    state_data=x[date][state_code]['districts']
    # ~ except:
      # ~ print 'no data for date: %s in state: %s' %(date,state_code)
      # ~ continue
    
    if district in state_data:
      district_data=state_data[district]
      if not ('total' in district_data and 'delta' in district_data): continue
      tested=0;tested_delta=0;deaths_delta=0;deaths=0;recovered=0
      confirmed=district_data['total']['confirmed']
      if 'recovered' in district_data['total']: recovered=district_data['total']['recovered']
      if 'deceased' in district_data['total']:  deaths=district_data['total']['deceased']
      if 'tested' in district_data['total']: tested=district_data['total']['tested']
      
      active=confirmed-recovered-deaths
      # ~ print active

      if not ('recovered' in district_data['delta'] and 'confirmed' in district_data['delta']): continue
      confirmed_delta=district_data['delta']['confirmed']
      try:
        recovered_delta=district_data['delta']['recovered']
      except:
        print(('error getting recovered_delta on date: '+date))
        print((district_data['delta']))
        return
      if 'deceased' in district_data['delta']: deaths_delta=district_data['delta']['deceased']
      active_delta=confirmed_delta-recovered_delta-deaths_delta
      if 'tested' in district_data['delta']: tested_delta=district_data['delta']['tested']

      if case_type=='confirmed_delta': returned.append((dt,confirmed_delta))
      elif case_type=='recovered_delta': returned.append((dt,recovered_delta))
      elif case_type=='deaths_delta': returned.append((dt,deaths_delta))
      elif case_type=='active_delta': returned.append((dt,active_delta))
      elif case_type=='tested_delta': returned.append((dt,tested_delta))
      elif case_type=='recovered': returned.append((dt,recovered))
      elif case_type=='deaths': returned.append((dt,deaths))
      elif case_type=='active': returned.append((dt,active))
      elif case_type=='tested': returned.append((dt,tested))
      elif case_type=='confirmed': returned.append((dt,confirmed))
    else:
      # ~ print 'district: %s not found in state: %s on date: %s' %(district,state,date)
      continue
      # ~ return
  del x
  if first30:
    date=''
    for i in returned:
      if i[1]>=30: return i[0]
  return returned
def plotex(dates,data,label='',color='blue',plot_days=''):
  if plot_days:
    dates=dates[-1*plot_days:]
    data=data[-1*plot_days:]
  if type(dates[0])==datetime.datetime: dates=pylab.date2num(dates)
  ax=pylab.axes()
  locator = mdates.AutoDateLocator(minticks=3, maxticks=7)
  formatter = mdates.ConciseDateFormatter(locator)
  ax.xaxis.set_major_locator(locator)
  ax.xaxis.set_major_formatter(formatter) 

  ax.set_xlabel('Date');ax.set_ylabel(label)
  ax.plot_date(dates,data,color=color,label=label)
  ax.tick_params(axis='y', labelcolor=color)
  #ax.legend(loc='lower left',fontsize=6)
  ax.legend(fontsize=7)
  title=label+' over time'
  pylab.title(title);  
  pylab.savefig(TMPDIR+title+'.jpg',dpi=100)
  pylab.close()


def plot2(dates,data,dates2,data2,label1='',label2='',state='',color1='blue',color2='red',plot_days=''):
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
    formatter = mdates.ConciseDateFormatter(locator)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(formatter) 

    ax.set_xlabel('Date')
    ax.set_ylabel(label1,color=color)
    ax.plot_date(dates,data,color=color,label=label1)
    ax.tick_params(axis='y', labelcolor=color)
    ax.legend(loc='lower left',fontsize=6)

    ax2=ax.twinx()
    color = color2
    locator = mdates.AutoDateLocator(minticks=3, maxticks=7)
    formatter = mdates.ConciseDateFormatter(locator)
    ax2.xaxis.set_major_locator(locator)
    ax2.xaxis.set_major_formatter(formatter) 

    ax2.set_ylabel(label2,color=color)
    ax2.plot_date(dates2,data2,color=color,label=label2)
    ax2.tick_params(axis='y', labelcolor=color)
    ax2.legend(loc='lower right',fontsize=6)
    
    title=''
    if state: title+=state+' '
    title+=label1.replace('(7-day MA)','')+' vs '+label2.replace('(7-day MA)','')
    pylab.title(title);  
    pylab.savefig(TMPDIR+title+'.jpg',dpi=100)
    pylab.close()



def get_national_data(case_type='active',verbose=False):
  pass
def get_beds(state='West Bengal',type=''):
    x=json.load(open('state_test_data.json'))
    x=[i for i in x['states_tested_data'] if i['state']==state and  i['bedsoccupiednormalisolation']]
    dates=[];bed_util=[];bed_cap=[]

    for i in x:
        dates.append(datetime.datetime.strptime(i['updatedon'],'%d/%m/%Y'))
        bed_cap.append(int(i['totalnumbedsnormalisolation']))
        u=int(bed_cap[-1]*0.01*float(i['bedsoccupiednormalisolation'].replace('%','')))
        bed_util.append(u)
    return list(zip(dates,bed_cap,bed_util)) 

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
    plot2(dates2,moving_average(bed_util),dates2,moving_average(ppe),label1='hospital beds used (7-day MA)',label2='daily PPE (7-day MA)',color2='maroon',state='West Bengal')
    plot2(dates2,moving_average(bed_util),dates2,moving_average(n95),label1='hospital beds used (7-day MA)',label2='daily N95 masks (7-day MA)',color2='grey',state='West Bengal')
    plot2(dates2,moving_average(bed_util),dates3,actives,label1='hospital beds used (7-day MA)',label2='Active cases (7-day MA)',color2='orange',state='West Bengal')
    plot2(dates2,moving_average(bed_util),dates4,deaths,label1='hospital beds used (7-day MA)',label2='Daily Deaths (7-day MA)',color2='red',state='West Bengal')


    return (dates,icu_cap,vent_cap,bed_cap,bed_util,ppe,n95)



def get_cases(state='Telangana',date='14/10/2020',case_type='active',return_full_series=False,verbose=False):
  x=json.load(open('states_daily.json'))['states_daily']

  target_datetime=datetime.datetime.strptime(date,'%d/%m/%Y')
  state_code=state_name_to_code[state]
  if case_type=='first100deaths':
    return_full_series=True

  #get all confirmed cases till date
  confirmed=0;recovered=0;deaths=0;active=0;
  confirmed_prev=0;recovered_prev=0;deaths_prev=0;active_prev=0;

  if return_full_series:
    confirmed_series={};recovered_series={};deaths_series={};active_series={};
    target_datetime=datetime.datetime.strptime(x[-1]['date'].replace('-20','-2020'),'%d-%b-%Y');#choose last date available
    
  for i in x:
    datetime_i=datetime.datetime.strptime(i['date'].replace('-20','-2020'),'%d-%b-%Y')
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
  if debug: print(download_cmd)
  os.system(download_cmd)
  (bulletin_date,annex_range)=karnataka_bulletin_parser('tmp.pdf',return_date_only=True)
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



def delhi_parse_csv():
    import csv,datetime
    r=csv.reader(open('csv_dumps/Delhi_Jun18_Oct27.csv'))
    info=[];skip=True
    for i in r: 
        #if skip: skip=False;continue
        x=i
        y=datetime.datetime(2020,int(x[0].split('-')[1]),int(x[0].split('-')[2]),0,0)
        x[0]=y
        a1,a2,a3,a4,a5,a6,a7,a8,a9,a10,a11,a12=x
        info.append(delhi_status(a1,int(a2),int(a3),int(a4),int(a5),int(a6),int(a7),int(a8),int(a9),int(a10),int(a11),int(a12)))

    return info
    
def delhi_bulletin_parser(bulletin='09_15_2020.pdf',return_date_only=False):
  cmd='pdftotext -layout "'+bulletin+'" tmp.txt';os.system(cmd)
  b=[i.strip() for i in open('tmp.txt').readlines() if i.strip()]

  date_string=[i for i in b if '2020' in i]
  if not date_string:
    print(('could not find date for bulletin ',bulletin))
    return
  date_string=date_string[0].lower()
  try:
    if '/' in date_string:
      date_string=date_string.split('/')[1].replace(')','').replace('(','').replace(',',' ').replace('2020',' ').strip()
    else:
      date_string=date_string.replace(')','').replace('(','').replace(',',' ').replace('2020',' ').strip()
  except:
    print(('error getting date for bulletin: '+bulletin+' with string: '+date_string))
  print(date_string)
  if len(date_string.split())==1: #all jumbled        
    for mm in ['june','july','august','september','october']: date_string=date_string.replace(mm,'')
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
  elif 'october' in month_string: month=10
  elif 'july' in month_string: month=7
  elif 'june' in month_string: month=6

  date=datetime.datetime(2020,month,day,0,0)

  if return_date_only: return date

  hos=[i for i in b if i.lower().startswith('hospital')]
  if not hos:
    print(('could not find data in bulletin %s for covid hospitals' %(bulletin)))
    return
  hos=hos[0];hos_capacity=hos.split()[-3];hos_used=hos.split()[-2];

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
  
  fig=plt.figure();
  ax=fig.gca();
  BLUE='#6699cc'
  # ~ colors=plt.cm.rainbow(numpy.linspace(0, 1, len(json_data['features'])))
  colors=plt.cm.hsv(numpy.linspace(0, 1, len(json_data['features'])))
  
  for feature,color in zip(json_data['features'],colors):
    poly=feature['geometry']
    patch=PolygonPatch(poly,fc=color,ec=color,alpha=0.5,zorder=2)
    ax.add_patch(patch);
    ax.axis('scaled');
  plt.axis('off')
  if plot_base: orig_date='BASEMAP'
  else: orig_date=orig_date.strftime('%b-%2d')
  plt.title(orig_date)
  plt.savefig(orig_date+'.png',bbox_layout='tight')
  plt.close()
  os.chdir('..')
  
  return (plt,ax,patch)

def chloropleth_data():
    data=[]
    states=list(state_name_to_code.keys());states.sort()
    for state in tqdm.tqdm(states):
        x=get_cases(state,case_type='confirmed',return_full_series=True)
        dates,confirmed=zip(*x)
        confirmed_delta=moving_average(np.diff(confirmed));dates=dates[1:]
        x=confirmed_delta
        for i in range(8,len(x)):#weekly change
            last=x[i-7]
            if last==0: continue
            percent_change=100*(float(x[i]-x[i-7])/x[i-7])
            sstate=state.replace('Odisha','Orissa').replace('Uttarakhand','Uttaranchal').replace(' Islands','')
            data.append((sstate,dates[i],percent_change))
    d2={}
    for i in data:
        st,d,p=i
        if d in d2:
            d2[d][st]=p
        else:
            d2[d]={st:p}
    #normalize d2
    for date in d2:
        ddict=d2[date]
        states,values=zip(*list(ddict.items()))
        vmax=np.max(values)
        vmin=np.abs(np.min(values))
        values2=[]
        for v in values:
            if v>0: values2.append(v/vmax)
            if v<0: values2.append(v/vmin)
        values=values2
        ddict2={}
        for i,j in zip(states,values2):
            ddict2[i]=j
        d2[date]=ddict2
    return data,d2

def chloropleth(data_dict={},date=''):
  from  matplotlib.colors import LinearSegmentedColormap
  from descartes import PolygonPatch;import matplotlib.pyplot as plt;import geojson
  #cmap=LinearSegmentedColormap.from_list('rg',["r", "y", "g"], N=256) 
  cmap=LinearSegmentedColormap.from_list('',["g", "y", "r"], N=256) 
  json_data=geojson.load(open('india_telengana.geojson'))

  fig=plt.figure();
  ax=fig.gca();
  #colors=plt.cm.hsv(numpy.linspace(0, 1, len(json_data['features'])))
  
  #for feature,color in zip(json_data['features'],colors):
  for feature in json_data['features']:
    poly=feature['geometry']
    name=feature.properties['NAME_1']
    if name in data_dict:
        data_value=data_dict[name]
        color=cmap(data_value)
#        if data_value<0: #green
#            color=[0,np.abs(data_value),0]
#        else: #red
#            color=[np.abs(data_value),0,0]
    else:
        print('Feature with name %s was not in data_dict' %(name))
        continue
    patch=PolygonPatch(poly,fc=color,ec=color,alpha=0.5,zorder=2)
    ax.add_patch(patch);
    ax.axis('scaled');
  plt.axis('off')
  orig_date=date.strftime('%b-%d')
  plt.title(orig_date)
  plt.savefig(TMPDIR+orig_date+'.png',bbox_layout='tight')
  print('saved to %s.png' %(orig_date))

def cartogram(window_size=3,ctype=''):
  # ~ d1=datetime.date(2020,5,1);d2=datetime.date(2020,9,23);delta=d2-d1
  d1=datetime.date(2020,8,1);d2=datetime.date(2020,9,28);delta=d2-d1
  dates=[(d1 + datetime.timedelta(days=i)) for i in range(delta.days + 1)]
  dates=dates[::window_size]
  for date in dates:
    str_date=date.strftime('%m_%d_%Y')
    print(('DATE: '+str_date))
    x=cartogram_date(str_date,window_size=window_size,verbose=False,ctype=ctype)
  
def karnataka_analysis(district='Bengaluru Urban',xlim=''):
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
  sp,ax=pylab.subplots()
  #pylab.clf()
  color = 'tab:blue'
  ax.set_xlabel('Date')
  ax.set_ylabel('ICU beds',color=color)
  ax.plot_date(dates2,ic,color=color,label=district+' ICU beds')
  if xlim: ax.set_xlim(xlim)
  ax.tick_params(axis='y', labelcolor=color)  

  ax2=ax.twinx()
  color = 'tab:red'
  ax2.set_ylabel('Daily deaths (7-day MA)',color=color)
  ax2.plot_date(dates,d,color=color,label=district+' daily deaths')
  ax2.tick_params(axis='y', labelcolor=color)

  sp.tight_layout()

  title=district+' ICU use vs daily deaths'
  pylab.title(title);
#  ax2.legend(loc='upper right');
#  ax.legend(loc='upper left');
#  pylab.legend();
#  pylab.show()
  pylab.savefig(TMPDIR+'karnataka_'+district+'_icu_vs_daily_deaths.jpg');pylab.close()
  
  print('plotting icu vs actives') 
  sp,ax=pylab.subplots()
  #pylab.clf()
  color = 'tab:blue'
  ax.set_xlabel('Date')
  ax.set_ylabel('ICU beds',color=color)
  ax.plot_date(dates2,ic,color=color,label=district+' ICU beds')
  ax.tick_params(axis='y', labelcolor=color)  

  ax2=ax.twinx()
  color = 'tab:orange'
  ax2.set_ylabel('Active Cases',color=color)
  ax2.plot_date(dates3,a,color=color,label=district+' active cases')
  ax2.tick_params(axis='y', labelcolor=color)

  sp.tight_layout()

  title=district+' ICU use vs active cases'
  pylab.title(title);  
#  ax2.legend(loc='lower right');
#  ax.legend(loc='lower left');
#  pylab.legend();
  #pylab.show()
  pylab.savefig(TMPDIR+'karnataka_'+district+'_icu_vs_actives.jpg');pylab.close()
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
      
    
def delhi_analysis(do='',plot_days=''):
  #hos_capacity='';hos_used='';dcc_capacity='';dcc_used='';dchc_capacity='';dchc_used='';
  # ~ hos_util=0;dcc_util=0;dchc_util=0
  # ~ total='';rtpcr='';rapid='';
  # ~ cz='';amb='';date=''
  # ~ import pylab
  if not do: do=delhi_parse_json()
  dates=[i.date for i in do]

  hos_used=[i.hos_used for i in do]
  dhc_used=[i.dchc_used for i in do]  
  dcc_used=[i.dcc_used for i in do]
  hos_cap=[i.hos_capacity for i in do]

  dates=pylab.date2num(dates)
  
  tot=[i.total for i in do]
  r=[i.rapid for i in do]
  rtpcr=[i.rtpcr for i in do]
  rp=numpy.float64(r)/numpy.float64(tot)

  cz=[i.cz for i in do]

  actives=get_cases(state='Delhi',case_type='active',return_full_series=True,verbose=True)
  deaths=get_cases(state='Delhi',case_type='deaths',return_full_series=True,verbose=True)
  dates2=[i[0] for i in actives]
  dates3=[i[0] for i in deaths]
  actives=[i[1] for i in actives]
  deaths=moving_average(numpy.diff([i[1] for i in deaths ]))
  deaths=deaths[-1*len(dates):]
   
  if len(actives)!=len(hos_used): actives=actives[-1*len(hos_used):]  

  hp=100*(numpy.float64(hos_used)/numpy.float64(actives))
  hc=100*(numpy.float64(hos_used)/numpy.float64(hos_cap))

  if plot_days:
      actives=actives[-1*plot_days:]
      hos_used=hos_used[-1*plot_days:]
      deaths=deaths[-1*plot_days:]
      dates=dates[-1*plot_days:]
      dates2=dates2[-1*plot_days:]
      dates3=dates3[-1*plot_days:]
  hos_used=moving_average(hos_used)
  actives=moving_average(actives)
  deaths=moving_average(deaths)
  plot2(dates,hos_used,dates2,actives,label1='Hospital beds used',label2='Active cases',color2='orange',state='Delhi')
  plot2(dates,hos_used,dates3,deaths,label1='Hospital beds used',label2='Daily Deaths',color2='red',state='Delhi')
  #plot2(dates,hp,dates,actives,label1='Hospitalization percentage (of actives)',label2='Active Cases',color1='blue',color2='orange',state='Delhi')
  plot2(dates,hc,dates,hos_cap,label1='Hospitalization percentage (of actives)',label2='Hospital (DCH) capacity',color1='blue',color2='orange',state='Delhi')
  return (dates,deaths)
  # ~ dhp=100*(numpy.float64(dhc_used)/numpy.float64(actives))
  # ~ ccp=100*(numpy.float64(dcc_used)/numpy.float64(actives))
  
  # ~ sp,ax=pylab.subplots()

  # ~ color = 'tab:blue'
  # ~ ax.set_xlabel('Date')
  # ~ ax.set_ylabel('Hospitalization (DCH) Percent (of active cases)',color=color)
  # ~ ax.plot_date(dates,hp,color=color,label='Hospitalization Percentage')
  # ~ ax.tick_params(axis='y', labelcolor=color)  

  # ~ ax2=ax.twinx()
  # ~ color = 'tab:green'
  # ~ ax2.set_ylabel('Health Center (DCHC) Percent (of active cases)',color=color)
  # ~ ax2.plot_date(dates,dhp,color=color,label='Health Center Percentage')
  # ~ ax2.tick_params(axis='y', labelcolor=color)

  # ~ sp.tight_layout()

  # ~ title='Hospitalion-percent(of actives) vs Health center percent in Delhi'
  # ~ pylab.title(title);
  # ~ ax2.legend(loc='upper right'); ax.legend(loc='upper left');
  # ~ pylab.legend();
  # ~ pylab.show()

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
  # ~ ax2.legend(loc='lower right'); ax.legend(loc='lower left');
  # ~ pylab.legend();
  # ~ pylab.show()


 

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
  # ~ ax.legend(loc='lower left');
  
  # ~ ax2=ax.twinx()
  # ~ color = 'tab:red'
  # ~ ax2.set_ylabel('Daily Deaths (7-day MA)',color=color)
  # ~ ax2.plot_date(dates[dates_skip:],deaths[dates_skip:],color=color,label='Daily Deaths (7-day MA)')
  # ~ ax2.tick_params(axis='y', labelcolor=color)
  # ~ ax2.legend(loc='lower right');
  
  # ~ sp.tight_layout()

  # ~ title='Hospital-beds-used vs Daily-deaths in Delhi'
  # ~ pylab.title(title);
  # ~ ax2.legend(loc='lower right'); 

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
  # ~ sp,ax=pylab.subplots()

  # ~ color = 'tab:blue'
  # ~ ax.set_xlabel('Date')
  # ~ ax.set_ylabel('DCH(hospital) beds',color=color)
  # ~ ax.plot_date(dates,hos_used,color=color,label='DCH(hospital) beds')
  # ~ ax.tick_params(axis='y', labelcolor=color)  
  # ~ ax.legend(loc='upper left');
  
  # ~ ax2=ax.twinx()
  # ~ color = 'tab:red'
  # ~ ax2.set_ylabel('DCHC(Health Center) beds',color=color)
  # ~ ax2.plot_date(dates,dhc_used,color=color,label='DCHC(Health Center) beds')
  # ~ ax2.tick_params(axis='y', labelcolor=color)
  # ~ ax2.legend(loc='lower left');
  
  # ~ sp.tight_layout()

  # ~ title='Bed Utilization in Delhi\'s Hospitals (DCH) and Health Centers (DCHC) over time'
  # ~ pylab.title(title);
  # ~ ax2.legend(loc='upper right'); 

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
  urls=['https://api.covid19india.org/states_daily.json','https://api.covid19india.org/data.json','https://api.covid19india.org/state_test_data.json','https://api.covid19india.org/data-all.json']
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
    if age.isdigit(): self.age=int(age)
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
        print(('error calculating death_reporting_interval with dor: '+str(self.date_of_reporting)+' and dod '+str(self.date_of_death)))
      
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
  
def moving_average(input_array=[],window_size=7,index_to_do_ma=1):
  x=input_array
  if type(input_array[0])==tuple:
    x=[i[index_to_do_ma] for i in input_array]
    dates=[i[0] for i in input_array]
    x2=numpy.convolve(x, numpy.ones((window_size,))/window_size, mode='valid')
    # ~ print type(x2),type(x[:window_size])
    x2=list(x[:window_size-1])+list(x2)
    # ~ d2=dates[window_size-1:]
    # ~ return zip(d2,x2)
    # ~ d2=dates[window_size-1:]
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
    print(("clipping buletin "+bulletin+"to  page range "+str(page_range)))
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
    bulletin_date=datetime.datetime.strptime(bulletin_date_string,'%d.%m.%Y')

    start=indices[j][0];end=indices[j+1][0]
    
    clip=b[start:end]
    death_case_no=clip[0].strip().split('Death Case No')[1].replace(':','').strip().replace('.','')
    cons=' '.join(clip[1:])

    
    try:
      age=cons.split()[1]
    except:
      print(('error splirtting cons: '+cons+' '+str(indices[j])))
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
  
def helper_plot_linear_fit(x,y,label='',color='',xtype='date'):
  # ~ import pylab
  xr=numpy.arange(len(x))
  # ~ coef=numpy.polyfit(xr,y,1)
  coef=numpy.polyfit(x,y,1)
  poly1d_fn=numpy.poly1d(coef)
  # ~ pylab.plot(x,y, 'yo', x, poly1d_fn(x), '--k',label='Best linear fit')
  # ~ pylab.plot_date(x,poly1d_fn(xr), 'g',label='Best linear fit')
  if not color:    color='g'
  if not label:    label='Best linear fit'
  
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

def get_mobility(state='Uttar Pradesh',district='',do_moving_average=True,plot=False,plot_days=''):
    import csv;info=[]
    r=csv.reader(open('2020_India_mobility_report.csv'))
    for i in r: info.append(i);
    x=[i for i in info if i[2]==state and i[3]==district]
    y=[]
    for i in x:
      dt=datetime.datetime.strptime(i[7],'%Y-%m-%d')
#      try:
      recr=int(i[8])
      groc_phar=int(i[9])
#      except:
#          print('error parsing '+str(i))
#          continue
      parks=int(i[10])
      trans=int(i[11])
      wrksp=int(i[12])
      resi=int(i[13])
      avg=(recr+groc_phar+parks+trans+wrksp+resi)/6.
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
        if district: #compare with avg of district vs state
            dates2,x1,x2,x3,x4,x5,x6,state_avg=zip(*get_mobility(state=state,district=''))
            dates2=pylab.date2num(dates2);dates=pylab.date2num(dates)
            ax=pylab.axes()
            locator = mdates.AutoDateLocator(minticks=3, maxticks=7)
            formatter = mdates.ConciseDateFormatter(locator)
            ax.xaxis.set_major_locator(locator)
            ax.xaxis.set_major_formatter(formatter) 
            ax.plot_date(dates,avg,label=district+' avg. change from baseline')
            ax.plot_date(dates2,state_avg,label=state+' avg. change from baseline')
            ax.set_xlabel('dates');ax.set_ylabel('Percent Change in mobility from baseline in '+district+' vs whole '+state);
            ax.legend(fontsize=6)
            ax.set_title('Mobility trends in '+district+' vs '+state)

            pylab.savefig(TMPDIR+district+' vs '+state+' mobility trends.jpg');pylab.close()

        else:
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
            formatter = mdates.ConciseDateFormatter(locator)
            ax.xaxis.set_major_locator(locator)
            ax.xaxis.set_major_formatter(formatter) 
            ax.plot_date(dates,recr,label='Retail')
            ax.plot_date(dates,groc,label='Grocery')
            ax.plot_date(dates,parks,label='Parks')
            ax.plot_date(dates,trans,label='Transport')
            ax.plot_date(dates,wrksp,label='Workplace')
            ax.plot_date(dates,resi,label='Residence')
            ax.set_xlabel('dates');ax.set_ylabel('Percent Change in mobility from baseline');
            ax.legend(fontsize=6)
            loc=state
            if district: loc=district+' district of '+state
            if not loc: loc='India'
            ax.set_title('Mobility trends in '+loc)

            pylab.savefig(TMPDIR+loc+' mobility trends.jpg');pylab.close()
            #avg vs pos
            if loc!='India':
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
def helper_get_mean_deaths(deaths,filter_type='',date_type='',moving_average=True,ma_size=3,state='Tamil Nadu',plot=False):
  d1=datetime.date(2020,6,1);d2=datetime.date(2020,10,22);delta=d2-d1
  datetimes=[(d1 + datetime.timedelta(days=i)) for i in range(delta.days + 1)]
  datetimes=[datetime.datetime.combine(i,datetime.time(0, 0)) for i in datetimes]

  mean_values=[];capital='bengaluru';outside=''
  
  ma_delta=datetime.timedelta(days=ma_size)
  if state=='Tamil Nadu':capital='chennai';outside='RoTN'
  elif state=='Kerala':capital='Thiruvananthapuram';outside='RoKL'

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
  if plot:
    mean_values=mean_values[:-5]
    if filter_type=='death_reporting': mean_values=mean_values[:-5]
    dates,m,m1,m2=zip(*mean_values)
    xlabel='';ylabel='';title=''
    if date_type=='':      xlabel='Date of death'
    elif date_type=='admission':      xlabel='Date of admission'
    elif date_type=='reporting':      xlabel='Date of reporting'
    ax=pylab.axes()
    locator = mdates.AutoDateLocator(minticks=3, maxticks=7)
    formatter = mdates.ConciseDateFormatter(locator)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(formatter) 

    if filter_type=='':      label='Mean age'
    if filter_type=='gender':      label='Percentage of Males in daily deaths'
    if filter_type=='comorb':      label='Percentage of deaths iwth NO comorbidities among daily deaths'
    if filter_type=='admission_death':      label='Admission-Death interval'
    if filter_type=='death_reporting':      label='Death-Reporting interval'
    #mean age vs time
    ax.plot_date(pylab.date2num(dates),m,label=label);
    title=label+' for '+state+' (over time)'
    pylab.xlabel(xlabel);pylab.ylabel(label);pylab.title(title);
    helper_plot_linear_fit(pylab.date2num(dates),m);
    ax.legend(fontsize=7)

    pylab.savefig(TMPDIR+title+'.jpg');pylab.close()

    ax=pylab.axes()
    locator = mdates.AutoDateLocator(minticks=3, maxticks=7)
    formatter = mdates.ConciseDateFormatter(locator)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(formatter) 

    #chn and rotn
    ax.plot_date(pylab.date2num(dates),m1,label=label+'('+capital+')');
    ax.plot_date(pylab.date2num(dates),m2,label=label+' ('+outside+')');
    title=label+' for '+capital+' and '+outside+' (over time)'
    pylab.xlabel(xlabel);pylab.ylabel(label);pylab.title(title);
    ax.legend(fontsize=7)
    pylab.savefig(TMPDIR+title+'.jpg');pylab.close()


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
    print(('parsing '+pdf))
    cmd='pdftotext -nopgbrk -layout "'+pdf+'" tmp.txt';os.system(cmd)
  
    b=[i.strip() for i in open('tmp.txt').readlines() if i.strip()][3:]
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
def get_antigen_tests(state='Karnataka',verbose=False):
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
    all_antigen.append((date,tests_on_day,antigen_on_day,percent_antigen))
  
  if verbose:
    print(('For state: %s' %(state)))
    for i in all_antigen:
      (date,tests_on_day,antigen_on_day,percent_antigen)=i
      print(('%s: %d tests,  %.1f percent (%d tests) were antigen' %(date,tests_on_day,percent_antigen,antigen_on_day)))
  return all_antigen

def get_tests(state='Karnataka',date='',return_full_series=True,verbose=False):
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
  return all_tests

def get_positivity_district(state='Karnataka',district='Bengaluru Urban',plot=False):
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
        import matplotlib.dates as mdates
        sp,ax=pylab.subplots()
        locator = mdates.AutoDateLocator(minticks=3, maxticks=7)
        formatter = mdates.ConciseDateFormatter(locator)
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(formatter) 
        color='tab:green'
        dates=pylab.date2num(dates)
        ax.plot_date(dates[-70:],p[-70:],color=color,label=district+' TPR (7-day MA)')
        xlabel='dates';ylabel='TPR (7-day MA)'
        ax.tick_params(axis='y', labelcolor=color)
        ax.set_xlabel(xlabel,color=color);ax.set_ylabel(ylabel,color=color);

        ax2=ax.twinx()
        color='tab:blue'
        ax2.tick_params(axis='y', labelcolor=color)
        ax2.plot_date(dates[-70:],t[-70:],color=color,label=district+' daily tests (7-day MA)')
        xlabel='dates';ylabel='daily tests (7-day MA)'
        ax2.tick_params(axis='y', labelcolor=color)
        ax2.set_xlabel(xlabel,color=color);ax2.set_ylabel(ylabel,color=color);

        pylab.title(district+' TPR vs daily tests')
        sp.tight_layout()

        pylab.savefig(TMPDIR+district+' TPR vs daily tests.jpg');pylab.close()
    return dates,p,c,t


def get_positivity(state='Karnataka',do_moving_average=True,plot=False,plot_days=''):
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
  all_ventilator_data=[i for i in x['states_tested_data'] if i['peopleonventilator'] and i['state']==state]
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

def analysis(state='Uttar Pradesh',extra=False,plot_days=''):
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
  sp,ax=pylab.subplots()
    
  locator = mdates.AutoDateLocator(minticks=3, maxticks=7)
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

  sp,ax=pylab.subplots()

  color = 'black'
  locator = mdates.AutoDateLocator(minticks=3, maxticks=7)
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
      ad=[datetime.datetime.strptime(i[0],'%d/%m/%Y') for i in yy]
      ad=pylab.date2num(ad)
      if plot_days:
          ap=ap[-1*plot_days:]
          ad=ad[-1*plot_days:]
      
      sp,ax=pylab.subplots()
      locator = mdates.AutoDateLocator(minticks=3, maxticks=7)
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
    os.system('mkdir -p webp')
    for i in tqdm.tqdm(x,desc='making webp'):
        y=Image.open(i)
        y.save('webp/'+os.path.splitext(i)[0]+'.webp')
        

def analysis_undercounting_karnataka(district='Bengaluru Urban',verbose=True):
  icu=karnataka_parse_icu_clipping()
  dates,ic=list(zip(*[(i.date,i.icu) for i in icu if i.district==district.replace(' ','')]))
  

  dates2,d=list(zip(*get_cases_district(state='Karnataka',district=district,case_type='deaths_delta')))
  if verbose: print(('got %s daily deaths' %(district)))
  dates3,a=list(zip(*get_cases_district(state='Karnataka',district=district,case_type='active')))

  ic=moving_average(ic);d=moving_average(d);a=moving_average(a)

  sp,ax=pylab.subplots()

  color = 'tab:blue'
  ax.set_xlabel('Date')
  ax.set_ylabel(district+'ICU usage (7-day MA)',color=color)
  ax.plot_date(pylab.date2num(dates),ic,color=color,label=district+' ICU usage (7-day MA)')
  ax.tick_params(axis='y', labelcolor=color)
#  ax.legend(loc='upper left');

  ax2=ax.twinx()
  color = 'tab:red'
  ax2.set_ylabel('Daily deaths (7-day MA)',color=color)
  ax2.plot_date(pylab.date2num(dates2),d,color=color,label=district+' daily deaths (7-day MA)')
  ax2.tick_params(axis='y', labelcolor=color)
#  ax2.legend(loc='lower right');
  # ~ sp.tight_layout()

  title=district+' ICU use vs daily deaths'
  pylab.title(title);

  
  sp,ax=pylab.subplots()

  color = 'tab:blue'
  ax.set_xlabel('Date')
  ax.set_ylabel(district+'ICU usage (7-day MA)',color=color)
  ax.plot_date(pylab.date2num(dates),ic,color=color,label=district+' ICU usage (7-day MA)')
  ax.tick_params(axis='y', labelcolor=color)
#  ax.legend(loc='upper left');

  ax2=ax.twinx()
  color = 'tab:orange'
  ax2.set_ylabel('Active cases (7-day MA)',color=color)
  ax2.plot_date(pylab.date2num(dates3),a,color=color,label=district+' active cases (7-day MA)')
  ax2.tick_params(axis='y', labelcolor=color)
#  ax2.legend(loc='lower right');
  # ~ sp.tight_layout()

  title=district+' ICU use vs active cases'
  pylab.title(title);
  
  
def analysis_undercounting(state='Haryana',atype='ventilator',plot_days=''):
  if atype in ['ventilator','ventilators']:
    y=get_people_on_ventilators(state)
  elif atype in ['icu','icus']:
    y=get_people_in_icus(state)
  elif atype in ['beds','hospital beds']:
    y=get_beds(state)
  if atype in ['beds','hospital beds']:
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
