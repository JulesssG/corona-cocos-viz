#!/usr/bin/env python
# coding: utf-8

# # Data generation notebook
# 
# Processing and generating data files for easier use

# In[31]:


import pandas as pd
import pycountry_convert as pc
import numpy as np
import warnings
warnings.filterwarnings('ignore')


# ## Load data

# In[32]:


data_frames = {
    'confirmed':  pd.read_csv('https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_global.csv'),
    'deaths': pd.read_csv('https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_global.csv'),
    'recovered': pd.read_csv('https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_recovered_global.csv')
}


# ## Remove cruises

# In[33]:


for key in data_frames.keys():
    df = data_frames[key]
    
    df = df[df['Country/Region'] != 'Diamond Princess']
    df = df[df['Country/Region'] != 'MS Zaandam']
    
    data_frames[key] = df


# ## Rename countries

# In[34]:


for key in data_frames.keys():
    df = data_frames[key]
    
    df = df.replace("Cote d'Ivoire", 'Ivory Coast')
    df = df.replace("Cabo Verde", 'Cape Verde')
    df = df.replace("Congo (Brazzaville)", 'Congo')
    df = df.replace("Congo (Kinshasa)", 'Democratic Republic of the Congo')
    df = df.replace("Czechia", 'Czech Republic')
    df = df.replace("Holy See", 'Vatican City')
    df = df.replace("Korea, South", 'South Korea')
    df = df.replace("Taiwan*", 'Taiwan')
    df = df.replace("US", 'United States')
    df = df.replace("West Bank and Gaza", 'State of Palestine')
    df = df.replace("Burma", 'Myanmar')
    
    data_frames[key] = df


# ## Separate 'countries' such as Greenland

# In[35]:


for key in data_frames.keys():
    df = data_frames[key]
    
    regions = ['Greenland', 'French Guiana', 'Falkland Islands (Malvinas)', 'New Caledonia']
    
    for region in regions:
        df.loc[df['Province/State'] == region, 'Country/Region'] = region
        
    data_frames[key] = df


# ## Group by country

# In[36]:


for key in data_frames.keys():
    df = data_frames[key]
    df = df.drop(columns='Province/State')
    
    # Compute average of Lat and Long
    agg_dict = {'Lat': 'mean',
                'Long': 'mean'}
    
    # Sum the rest of the columns
    for column in df.columns[3:]:
        agg_dict[column] = 'sum'
    
    data_frames[key] = df.groupby('Country/Region').agg(agg_dict).reset_index()


# ## Reformat dates

# In[37]:


for key in data_frames.keys():
    df = data_frames[key]
    dates = [x.strftime("%Y-%m-%d") for x in pd.to_datetime(df.columns[3:])]
    df.columns = list(df.columns[:3]) + dates


# ## Add world population column

# In[38]:


population_df = pd.read_csv('generated/population.csv')

for key in data_frames.keys():
    df = data_frames[key]
    
    df = df.merge(population_df, how='left', left_on='Country/Region', right_on='name')
    df = df.drop(columns='name')
    
    # Reorder columns
    df = df[['Country/Region', 'population'] + list(df.columns[1:-1])]
    df = df.copy()
    
    data_frames[key] = df


# ## Add sick dataset (confirmed - recovered)

# In[39]:


confirmed = data_frames['confirmed']
recovered = data_frames['recovered']
# Check that the countries are in the same order
assert((confirmed.loc[:, 'Country/Region'] != recovered.loc[:, 'Country/Region']).sum() == 0)

sick = confirmed.copy()
sick.loc[:, sick.columns[4:]] = confirmed.loc[:, sick.columns[4:]] - recovered.loc[:, sick.columns[4:]]
data_frames['sick'] = sick


# ## Add daily dataset (number of confirmed cases for each day)

# In[40]:


daily = data_frames['confirmed'].copy()

days = daily.loc[:, daily.columns[5:]]
shifted_days = daily.loc[:, daily.columns[4:-1]]
shifted_days.columns = days.columns

daily.loc[:, daily.columns[5:]] = days - shifted_days
data_frames['daily'] = daily


# ## Add world and continents rows

# In[41]:


# Continents code to name
continents = {
    'AF': 'Africa',
    'AS': 'Asia',
    'EU': 'Europe',
    'NA': 'North America',
    'OC': 'Oceania',
    'SA': 'South America'
}

def country_to_continent(country):
    """
    From country name get continent name
    """
    try:
        country_code = pc.country_name_to_country_alpha2(country)
        continent = pc.country_alpha2_to_continent_code(country_code)
        return continents[continent]
    except:
        # Country unknown for pycountry -> by hand
        if country == 'Kosovo':
            return 'Europe'
        elif country == 'State of Palestine':
            return 'Asia'
        elif country == 'Timor-Leste':
            return 'Asia'
        elif country == 'Vatican City':
            return 'Europe'
        elif country == 'Western Sahara':
            return 'Africa'
        else:
            print(f"Unkown country continent: {country}")
            raise ValueError

            
for key in data_frames.keys():
    df = data_frames[key].copy()
    
    # Compute world aggregation
    world = pd.Series(df.loc[0, :])
    world['Country/Region'] = "World"
    world['population'] = df['population'].sum()
    world['Lat'] = 0
    world['Long'] = 0
    world.loc[world.index[4:]] = df.loc[:, df.columns[4:]].sum()
    world = pd.DataFrame(world).T
    
    # Compute continents aggregation
    df['Country/Region'] = df['Country/Region'].apply(country_to_continent)
    
    # Aggregation dict
    agg_dict = {'population': 'sum',
                'Lat': 'mean',
                'Long': 'mean'}
    
    # Sum the rest of the columns
    for column in df.columns[4:]:
        agg_dict[column] = 'sum'
    
    df = df.groupby('Country/Region').agg(agg_dict).reset_index()
    
    # Concat world, continents and countries
    df = pd.concat([world, df, data_frames[key]]).reset_index(drop=True)
    data_frames[key] = df


# ## Write back data

# In[42]:


for key in data_frames.keys():
    data_frames[key].to_csv(f'generated/{key}.csv', index=False)


# ## Governments measures generation

# In[49]:


from urllib.request import urlopen
try:
    _ = urlopen('https://www.acaps.org/sites/acaps/files/resources/files/acaps_covid19_government_measures_dataset.xlsx')
    url = 'https://www.acaps.org/sites/acaps/files/resources/files/acaps_covid19_government_measures_dataset.xlsx'
except:
    _ = urlopen('https://www.acaps.org/sites/acaps/files/resources/files/acaps_covid19_government_measures_dataset_0.xlsx')
    url = 'https://www.acaps.org/sites/acaps/files/resources/files/acaps_covid19_government_measures_dataset_0.xlsx'

sheets = pd.ExcelFile(url).sheet_names
ind = np.where(['data' in sheet.lower() for sheet in sheets])[0][0]
data_full = pd.read_excel(url, sheet_name=sheets[ind])

data_full.columns = [s.strip('_') for s in data_full.columns]

data_full.loc[data_full['DATE_IMPLEMENTED'].isna(), 'DATE_IMPLEMENTED'] = data_full.loc[data_full['DATE_IMPLEMENTED'].isna(), 'ENTRY_DATE']


# In[50]:


data = data_full[['COUNTRY', 'LOG_TYPE', 'CATEGORY', 'MEASURE', 'COMMENTS', 'DATE_IMPLEMENTED']]
data['MEASURE'] = data['MEASURE'].str.replace('\xa0', '')
data


# Match the countries, delete the countries that are not in our dataset on corona cases

# In[64]:


original = pd.read_csv('generated/confirmed.csv')

country_matching = {'Viet Nam': 'Vietnam',
                   'United States of America': 'United States',
                   'Russian Federation': 'Russia',
                   'Palestine': 'State of Palestine',
                   'North Macedonia Republic Of': 'North Macedonia',
                   'Moldova Republic Of': 'Moldova',
                   'Moldova Republic of': 'Moldova',
                   'Lao PDR': 'Laos',
                   'Korea Republic of': 'South Korea',
                   'kenya': 'Kenya',
                   'Czech republic': 'Czech Republic',
                   "Côte d'Ivoire": 'Ivory Coast',
                   'Cabo Verde': 'Cape Verde',
                   'Brunei Darussalam': 'Brunei',
                   'Congo DR': 'Democratic Republic of the Congo'}

others = ['Turkmenistan', 'Vanuatu', 'Tuvalu', 'Tonga', 'Tajikistan', 'Solomon Islands', 
          'Samoa', 'Palau', 'Nauru', 'Micronesia', 'Marshall Islands', 'Lesotho', 'Korea DPR',
          'Kiribati', 'Comoros', 'China, Hong Kong Special Administrative Region']

# Delete countries present in measure dataset without match in original (manual)
data = data.loc[~data['COUNTRY'].isin(others), :]

# Delete countries present in measure dataset without match in original (automatic)
# Can check in countries_without_match_df to see if it's possible to match more countries
data['COUNTRY'] = data['COUNTRY'].replace(country_matching)
countries_without_match_df = (data[['COUNTRY']].drop_duplicates()
                              .merge(original[['Country/Region']], 
                                     how='outer', 
                                     left_on='COUNTRY', 
                                     right_on='Country/Region'))
countries_without_match = countries_without_match_df.loc[countries_without_match_df['Country/Region'].isna(), 
                                                         'COUNTRY']
data = data.loc[~data['COUNTRY'].isin(countries_without_match)]

# Double check
check_match = (data[['COUNTRY']].drop_duplicates()
               .merge(original[['Country/Region']], 
                      how='outer', 
                      left_on='COUNTRY', 
                      right_on='Country/Region')['Country/Region'].isna().sum())
print('Number of incorrectly named countries relative to original dataset:', check_match)


# In[46]:


data.columns = ['country', 'log_type', 'category', 'measure', 'comment', 'date']
data['date'] = pd.to_datetime(data['date']).dt.strftime('%Y-%m-%d') 
data.to_csv('generated/governments-measures.csv', index=False)
data

