from bs4 import BeautifulSoup
import requests
import re
import pandas as pd
import ast
import numpy as np
from skimage import io
from scipy import ndimage
from skimage.color import rgb2hsv
from sklearn.decomposition import PCA
    
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
    mondrian = mondrian.reset_index(drop=True)
    
    def rgb_and_hsv(df):
        rgb_imgs = list()
        hsv_imgs = list()
        for i in df['image link']:
            p = io.imread(i)
            rgb_imgs.append(p)
            if len(p.shape) != 3:
                hsv_imgs.append(np.NaN)
                continue
            hsv_img = rgb2hsv(p)
            hsv_imgs.append(hsv_img)
        df.rgb = rgb_imgs
        df.hsv = hsv_imgs
        return df
    
    def hue_saturation_edge(df):
        mean_hues = list()
        mean_sats = list()
        edge_scores = list()
        count=0
        
        for hsv_img in df.hsv:
            if count % 50 == 0:
                print(count)
                
            if type(hsv_img) == float:
                mean_hues.append(np.NaN)
                mean_sats.append(np.NaN)
                edge_scores.append(np.NaN)
                count += 1
                continue
            
            hue_img = hsv_img[:, :, 0]
            mean_hue = np.mean(hue_img, axis=(0,1))
            mean_hues.append(mean_hue)
            
            value_img = hsv_img[:, :, 2]
            
            sat_img = hsv_img[:, :, 1]
            mean_sat = np.mean(sat_img, axis=(0,1))
            mean_sats.append(mean_sat)
            
            sobel_x = ndimage.sobel(value_img, axis=0, mode='constant')
            sobel_y = ndimage.sobel(value_img, axis=1, mode='constant')
            edge_image = np.hypot(sobel_x, sobel_y)
            edge_score = np.sum(edge_image)
            edge_scores.append(edge_score)
        
        df['mean_hue'] = mean_hues
        df['mean_saturation'] = mean_sats
        df['edge_score'] = edge_scores
        
        return df
    
    def value(df):
        vals = list()
        for hsv_img in df.hsv:
            if type(hsv_img) == float:
                vals.append(np.NaN)
                continue
            value_img = hsv_img[:, :, 2]
            mean_value = np.mean(value_img, axis=(0,1))
            vals.append(mean_value)
        df['mean_value'] = vals
        return df
    
    def pca(df):
        feats = df.dropna()
        pca = PCA(n_components=2)
        pca_result = pca.fit_transform(feats[['end date', 'resolution', 'mean_hue', 'mean_saturation', 'mean_value', 'edge_score']].values)
        feats['pca-one'] = pca_result[:,0]
        feats['pca-two'] = pca_result[:,1]
        return feats
        
    mondrian = rgb_and_hsv(mondrian)
    mondrian = hue_saturation_edge(mondrian)
    mondrian = value(mondrian)
    mondrian = pca(mondrian)
    
    def color_score(df):
        n_colors = list()
        for i in df.rgb:
            if type(i) == float or len(i.shape) == 2:
                n_colors.append(np.NaN)
                continue
                
            colors = list()
            for row in i:
                for c in row:
                    colors.append(c)
            
            colors = pd.Series(colors).apply(lambda a: list(a))
            n = len(np.unique(colors))
            n_colors.append(n)
        df['color_score'] = n_colors
        return df
    
    def variance_score(df):
        var_scores = list()
        for p in df.hsv:
            if type(p) == float or len(p.shape) == 2:
                var_scores.append(np.NaN)
                continue
            value_img = p[:, :, 2]
            img_vars = list()
            for row in value_img:
                var = np.var(row)
                img_vars.append(var)
            var_scores.append(np.mean(img_vars))
        df['variance_score'] = var_scores
        return df
    
    def complexity(df):
        df.edge_score = df.edge_score.apply(lambda x: x/np.max(df.edge_score))
        df.color_score = df.color_score.apply(lambda x: x/np.max(df.color_score))
        df.variance_score = df.variance_score.apply(lambda x: x/np.max(df.variance_score))
        return df
    
    mondrian = color_score(mondrian)
    mondrian = variance_score(mondrian)
    mondrian = complexity(mondrian)
    
    return mondrian

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