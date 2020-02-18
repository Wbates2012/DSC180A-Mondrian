from bs4 import BeautifulSoup
import requests
import re
import pandas as pd
import ast
import numpy as np
from skimage import io
    
def data():
    
    config = list()
    url = 'https://rkd.nl/en/explore/images/record?filters%5Bkunstenaar%5D%5B0%5D=Mondriaan%2C+Piet&query=piet+mondrian&sort%5Bsort_startdate%5D=asc&start='
    for i in range(1481):
        extra = str(i)
        painting = url + extra
        config.append(painting)
    
    def painting_details(url):
        painting = dict()
        doc = requests.get(url)
        soup = BeautifulSoup(doc.text)
        # Get ID
        pat = '\d+\d'
        patnan0 = '>na<'
        patnan1 = 'digital'
        for i in range(10):
            if soup.find_all("div", {"class": 'text'})[i].string[0:8]  == 'Location':
                s = str(soup.find_all("div", {"class": 'text'})[i].next_element.next_element)
                if len(re.findall(patnan0, s)) > 0 or len(re.findall(patnan1, s)) > 0:
                    painting['title'] = 'na'
                    painting['date'] = 'na'
                    painting['image link'] = 'na'
                    painting['id'] = 'na'
                    return painting
                num = re.findall(pat, s)[0]
                break
        # Get Image Link
        image_link = soup.find_all('meta')[9]['content']
        # Get Title
        if soup.find(string='English title') == None:
            title = 'na'
        else:
            title = soup.find(string='English title').next_element.next_element.text.strip()
        # Get Date
        for i in range(5):
            if soup.find_all("div", {"class": 'text'})[i].string[0:5]  == 'Exact':
                date = soup.find_all("div", {"class": 'text'})[i].next_element.next_element.next_element.next_element.strip()
                break
        # Get Category
        category = soup.find_all('a', {'class': 'thesaurus'})[0].string
        painting['title'] = title
        painting['date'] = date
        painting['image link'] = image_link
        painting['id'] = num
        painting['category'] = category
        return painting
    
    # Takes a long time
    mondrian = list()
    for u in config:
        painting = painting_details(u)
        mondrian.append(painting)
    
    with open('mondrian.txt', 'w') as fh:
        for item in mondrian:
            fh.write('%s\n' % item)
            
def process(datatxt):
    # Create dataframe of extracted data
    df = []
    for l in open(datatxt):
        row = l[:-1]
        df.append(ast.literal_eval(row))
    mondrian = pd.DataFrame(df)
    
    def remove_nans(df):
        for col in list(df.columns):
            df[col] = [np.NaN if i=='na' else i for i in df[col]]
        df = df.dropna()
        df = df.reset_index(drop=True)
        return df
    
    def clean_dates(df):
        
        def clear_parens(df):
            pat = '\(.*\)'
            dts = list()
            for s in df.date:
                if len(re.findall(pat, s)) == 0:
                    dts.append(s)
                else:
                    dts.append(s.replace(re.findall(pat, s)[0], ' '))
            df.date = dts
            return df
        
        def split_dates(df):
            start = list()
            end = list()
            count = 0
            for s in df.date:
                l = re.findall('[0-9]{4}', s)
                if len(l) == 1:
                    start.append(int(l[0]))
                    end.append(int(l[0]))
                else:
                    start.append(int(l[0]))
                    end.append(int(l[1]))
                count+=1
            
            df['start date'] = start
            df['end date'] = end
            df = df.drop(['date'], axis=1)
            return df
        df = clear_parens(df)
        df = split_dates(df)
        return df
    
    def drop_bad_ids(df):
        return df[df.id != '82'].reset_index(drop=True)
    
    def clean_category(df):
        df.category = ['painting' if 'painting' in i else i for i in df.category]
        df.category = ['drawing' if 'sketch' in i else i for i in df.category]
        return df
    
    # Takes a long time
    def get_resolutions(df):
        resos = list()
        for image in df['image link']:
            arr = io.imread(image)
            res = arr.shape[0]*arr.shape[1]
            resos.append(res)
        df['resolution'] = resos
        return df
    
    def limit_to_paintings(df):
        return df[df.category == 'painting']
    
    def remove_low_res(df):
        return df[df.resolution > df.resolution.mean() - 2*df.resolution.std()]
        
    mondrian = remove_nans(mondrian)
    mondrian = clean_dates(mondrian)
    mondrian = drop_bad_ids(mondrian)
    mondrian = clean_category(mondrian)
    mondrian = get_resolutions(mondrian)
    mondrian = limit_to_paintings(mondrian)
    
    return mondrian.reset_index(drop=True)

def data_test():
    
    # Configuration list
    config = list()
    url = 'https://rkd.nl/en/explore/images/record?filters%5Bkunstenaar%5D%5B0%5D=Mondriaan%2C+Piet&query=piet+mondrian&sort%5Bsort_startdate%5D=asc&start='
    for i in range(50):
        extra = str(i)
        painting = url + extra
        config.append(painting)
    
    def painting_details(url):
        painting = dict()
        doc = requests.get(url)
        soup = BeautifulSoup(doc.text)
        # Get ID
        pat = '\d+\d'
        patnan0 = '>na<'
        patnan1 = 'digital'
        for i in range(10):
            if soup.find_all("div", {"class": 'text'})[i].string[0:8]  == 'Location':
                s = str(soup.find_all("div", {"class": 'text'})[i].next_element.next_element)
                if len(re.findall(patnan0, s)) > 0 or len(re.findall(patnan1, s)) > 0:
                    painting['title'] = 'na'
                    painting['date'] = 'na'
                    painting['image link'] = 'na'
                    painting['id'] = 'na'
                    return painting
                num = re.findall(pat, s)[0]
                break
        # Get Image Link
        image_link = soup.find_all('meta')[9]['content']
        # Get Title
        if soup.find(string='English title') == None:
            title = 'na'
        else:
            title = soup.find(string='English title').next_element.next_element.text.strip()
        # Get Date
        for i in range(5):
            if soup.find_all("div", {"class": 'text'})[i].string[0:5]  == 'Exact':
                date = soup.find_all("div", {"class": 'text'})[i].next_element.next_element.next_element.next_element.strip()
                break
        # Get Category
        category = soup.find_all('a', {'class': 'thesaurus'})[0].string
        painting['title'] = title
        painting['date'] = date
        painting['image link'] = image_link
        painting['id'] = num
        painting['category'] = category
        return painting
    
    mondrian = list()
    for u in config:
        painting = painting_details(u)
        mondrian.append(painting)
    
    with open('mondrian.txt', 'w') as fh:
        for item in mondrian:
            fh.write('%s\n' % item)
            
# data()
data_test()
process('mondrian.txt')