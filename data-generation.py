#!/usr/bin/env python
# coding: utf-8

# # Data generation notebook
#
# Processing and generating data files for easier use

# In[1]:


import pandas as pd
import pycountry_convert as pc
import numpy as np


# ## Load data

# In[2]:


data_frames = {
    'confirmed':  pd.read_csv('https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_global.csv'),
    'deaths': pd.read_csv('https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_global.csv'),
    'recovered': pd.read_csv('https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_recovered_global.csv')
}


# ## Remove cruises

# In[3]:


for key in data_frames.keys():
    df = data_frames[key]

    df = df[df['Country/Region'] != 'Diamond Princess']
    df = df[df['Country/Region'] != 'MS Zaandam']

    data_frames[key] = df


# ## Rename countries

# In[4]:


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

# In[5]:


for key in data_frames.keys():
    df = data_frames[key]

    regions = ['Greenland', 'French Guiana', 'Falkland Islands (Malvinas)', 'New Caledonia']

    for region in regions:
        df.loc[df['Province/State'] == region, 'Country/Region'] = region

    data_frames[key] = df


# ## Group by country

# In[6]:


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

# In[7]:


for key in data_frames.keys():
    df = data_frames[key]
    dates = [x.strftime("%Y-%m-%d") for x in pd.to_datetime(df.columns[3:])]
    df.columns = list(df.columns[:3]) + dates


# ## Add world population column

# In[8]:


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

# In[9]:


confirmed = data_frames['confirmed']
recovered = data_frames['recovered']
# Check that the countries are in the same order
assert((confirmed.loc[:, 'Country/Region'] != recovered.loc[:, 'Country/Region']).sum() == 0)

sick = confirmed.copy()
sick.loc[:, sick.columns[4:]] = confirmed.loc[:, sick.columns[4:]] - recovered.loc[:, sick.columns[4:]]
data_frames['sick'] = sick


# ## Add daily dataset (number of confirmed cases for each day)

# In[10]:


daily = data_frames['confirmed'].copy()

days = daily.loc[:, daily.columns[5:]]
shifted_days = daily.loc[:, daily.columns[4:-1]]
shifted_days.columns = days.columns

daily.loc[:, daily.columns[5:]] = days - shifted_days
data_frames['daily'] = daily


# ## Add world and continents rows

# In[11]:


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

# In[12]:


for key in data_frames.keys():
    data_frames[key].to_csv(f'generated/{key}.csv', index=False)


# ## Governments measures generation

# In[16]:


data_full = pd.read_excel('https://www.acaps.org/sites/acaps/files/resources/files/acaps_covid19_government_measures_dataset_0.xlsx', sheet_name="Database")
data_full.loc[data_full['DATE_IMPLEMENTED'].isna(), 'DATE_IMPLEMENTED'] = data_full.loc[data_full['DATE_IMPLEMENTED'].isna(), 'ENTRY_DATE']


# In[17]:


data = data_full[['COUNTRY', 'LOG_TYPE', 'CATEGORY', 'MEASURE', 'COMMENTS', 'DATE_IMPLEMENTED']]
data.loc[:, 'MEASURE'] = data['MEASURE'].str.replace('\xa0', '')


# Match the countries, delete the countries that are not in our dataset on corona cases

# In[18]:


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
data = data.loc[~data['COUNTRY'].isin(others), :]
data['COUNTRY'] = data['COUNTRY'].replace(country_matching)
number_countries_not_in_original_dataset = (data[['COUNTRY']]
                                            .drop_duplicates()
                                            .merge(original[['Country/Region']], how='outer', left_on='COUNTRY', right_on='Country/Region')['Country/Region'].isna().sum())
print('Number of incorrectly named countries relative to original dataset:', number_countries_not_in_original_dataset)


# In[19]:


data.columns = ['country', 'log_type', 'category', 'measure', 'comment', 'date']
data['date'] = pd.to_datetime(data['date']).dt.strftime('%Y-%m-%d')
data.to_csv('generated/governments-measures.csv', index=False)
