#!/usr/bin/python2

#code runs with python-2 (for python-3, just convert the "print" statements to function
#to install dependencies "pip install pylab json requests"

# ~ for moving average with window 'N'
# ~ np.convolve(x, np.ones((N,))/N, mode='valid')


import json,datetime,numpy,pylab

state_code_to_name={'pb':'Punjab',            'hr':'Haryana',
                    'kl':'Kerala',            'ka':'Karnataka',
                    'tg':'Telangana',         'gj':'Gujarat',
                    'dl':'Delhi',             'nl':'Nagaland',
                    'sk':'Sikkim',            'ct': 'Chhattisgarh',
                    'ap':'Andhra Pradesh',    'tn': 'Tamil Nadu',
                    'bh':'Bihar',             'up': 'Uttar Pradesh',
                    'as':'Assam',             'wb': 'West Bengal',
                    'mp':'Madhya Pradesh',    'jh': 'Jharkhand',
                    'rj':'Rajasthan',         'or': 'Odisha',
                    }
state_name_to_code={}
for k in state_code_to_name: state_name_to_code[state_code_to_name[k]]=k

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
def get_tests(state='Karnataka',verbose=False):
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
