#!/usr/bin/python2

#code runs with python-2 (for python-3, just convert the "print" statements to function
#to install dependencies "pip install pylab json requests"

import json,pylab,datetime

state_code_to_name={'pb':'Punjab',
                    'hr':'Haryana',
                    'kl':'Kerala',
                    'ka':'Karnataka',
                    'tg':'Telangana',
                    'gj':'Gujarat',
                    'dl':'Delhi',
                    'nl':'Nagaland',
                    }
state_name_to_code={}
for k in state_code_to_name: state_name_to_code[state_code_to_name[k]]=k

##date must be given as 01/09/2020 for September 1,2020
##State must be fullname (see dict above)
def get_active_cases(state='Telangana',date='01/09/2020',verbose=False):
  x=json.load(open('states_daily.json'))['states_daily']

  target_datetime=datetime.datetime.strptime(date,'%d/%m/%Y')
  state_code=state_name_to_code[state]

  #get all confirmed cases till date
  confirmed=0;recovered=0;deaths=0;active=0;
  
  for i in x:
    datetime_i=datetime.datetime.strptime(i['date'].replace('-20','-2020'),'%d-%b-%Y')
    if datetime_i<=target_datetime:
      if   i['status']=='Deceased':  deaths+=int(i[state_code])
      elif i['status']=='Recovered': recovered+=int(i[state_code])
      elif i['status']=='Confirmed': confirmed+=int(i[state_code])

  active=confirmed-deaths-recovered

  if verbose:    print 'Active cases in %s on %s were %d' %(state,date,active)
  return active

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
    actives_on_this_date=get_active_cases(state,date_of_entry)
    percent_icu=100*(float(icu_usage)/actives_on_this_date)
    all_percent_icu.append((date_of_entry,percent_icu,icu_usage))

  if verbose:
    print 'For state: %s, the variation of pecent of patients in ICU is ..' %(state)
    for i in all_percent_icu:
      print '%s : %.3f (%d in icu)' %(i[0],i[1],i[2])
  return all_percent_icu

  
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
    actives_on_this_date=get_active_cases(state,date_of_entry)
    percent_ventilator=100*(float(ventilator_usage)/actives_on_this_date)
    all_percent_ventilator.append((date_of_entry,percent_ventilator,ventilator_usage))

  if verbose:
    print 'For state: %s, the variation of pecent of patients on ventilator is ..' %(state)
    for i in all_percent_ventilator:
      print '%s : %.3f (%d on ventilator)' %(i[0],i[1],i[2])
  return all_percent_ventilator

def make_plots(use_all_states=False):
  
  states_icu=['Haryana','Karnataka','Delhi','Kerala']
  states_ventilator=['Delhi','Gujarat','Haryana','Kerala']

  #make ICU plot
  for state in states_icu:
    icu_data=get_people_in_icus(state)
    if not icu_data: continue
    dates=[i[0] for i in icu_data]
    dates=[datetime.datetime.strptime(i,'%d/%m/%Y') for i in dates]
    dates=pylab.date2num(dates)
    icu_percent=[i[1] for i in icu_data]
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
    pylab.plot_date(dates,ventilator_percent,label=state)
  pylab.xlabel('date');pylab.ylabel('percent of active cases on ventilator');pylab.legend()
  pylab.title('Ventilator use in states over time')
  pylab.show(); pylab.close()
  figure = pylab.gcf();figure.set_size_inches(8, 6);pylab.savefig('Ventilator_usage.png', dpi = 100);
    
if __name__=='__main__':
  make_plots()
