from datetime import datetime
import requests
from time import time

from bs4 import BeautifulSoup
from bs4.element import ResultSet, Tag
import pandas as pd


BASE_SEARCH_URL = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?'
BASE_FETCH_URL = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?'
DATABASE = 'pubmed'
RETMAX = '150' # maximum number of articles to scrape
DATE_TYPE = 'pdat' # publication date
MAX_DATE = '2025' # minimum publication date is 1781/01/01
MIN_DATE = '2010' 
USE_HISTORY = 'y'
SAVE_DIRECTORY = '/home/path/to/save/directory/'


def make_query(term: str) -> dict[str]:
    url = f'{BASE_SEARCH_URL}db={DATABASE}&term={term}&datetype={DATE_TYPE}&mindate={MIN_DATE}&maxdate={MAX_DATE}&usehistory={USE_HISTORY}'
    ids = requests.get(url)
    soup_ids = BeautifulSoup(ids.text, features='xml')
    query_key = soup_ids.find('QueryKey').text
    web_env = soup_ids.find('WebEnv').text
    return {'query_key': query_key, 'web_env': web_env}
    

def get_articles(key: str, env: str) -> BeautifulSoup:
    url = f'{BASE_FETCH_URL}db={DATABASE}&query_key={key}&WebEnv={env}&retmax={RETMAX}&retmode=xml&rettype=abstract'
    response = requests.get(url)
    return BeautifulSoup(response.text, features='xml')


def check_safe(obj: ResultSet[Tag]) -> str:
    try:
        return obj.text if obj else 'MISSING'
    except IndexError:
        return 'MISSING'
    

def extract_data(soup: BeautifulSoup) -> pd.DataFrame:
    
    articles = soup.find_all('PubmedArticle')
    records = []

    for article in articles:

        placeholder_dict = {
            'Title': check_safe(article.find('ArticleTitle')),
            'Abstract': ' '.join([check_safe(abstract) for abstract in article.find_all('AbstractText')]),
            'Doi': check_safe(article.find('ArticleId', {'IdType': 'doi'})),
            'Year': (article.find('PubDate').contents[0].text if article.find('PubDate') and article.find('PubDate').contents else 'MISSING')
        }
        
        initials = article.find_all('Initials')
        last_names = article.find_all('LastName')
        first_author = f'{last_names[0].text if last_names else "MISSING"}, {initials[0].text.replace('','.')[1:] if initials else ""}'
        last_author = f'{last_names[-1].text if last_names else "MISSING"}, {initials[-1].text.replace('','.')[1:] if initials else ""}'
        placeholder_dict['Authors'] = (rf'First Author: {first_author} \| Last Author: {last_author}' if first_author != last_author else f'First Author: {first_author if first_author else "MISSING"}')

        records.append(placeholder_dict)
    
    return pd.DataFrame(records)


def save_as_markdown(dataframe: pd.DataFrame) -> None:
    if not dataframe.empty:
        with open(f'{SAVE_DIRECTORY}{term.replace(' ', '-')+'-abstract-search'}.md', 'w', encoding='utf‑8') as f:
            f.write(f'# Searched for: {term.title()}\n\n')
            f.write(f'- **Entries:** {len(dataframe.index)}\n')
            f.write(f'- **Date:** {datetime.today().date()}\n')
            for _, row in dataframe.iterrows():
                f.write(f'## {row['Title']}\n\n')
                f.write(f'- **Authors:** {row['Authors']}\n')
                f.write(f'- **Year:** {row['Year']}\n')
                f.write(f'- **DOI:** {row['Doi']}\n\n')
                f.write(row['Abstract'].strip() + '\n\n')
                f.write('\n' + '='*120 + '\n\n\n')


def main() -> None:
    start_time = time()
    query = make_query(term=searched_term)
    article_soup = get_articles(key=query['query_key'], env=query['web_env'])
    final_data = extract_data(soup=article_soup)
    end_time = time()
    print(f'\nRetrieved {len(final_data.index)} articles in {(end_time-start_time):.2f} seconds...\nSaving data...')
    save_as_markdown(dataframe=final_data)


if __name__ == '__main__':
    term = input('What do you wish to search for?\n').lower()
    searched_term = term.replace(' ', '+') + '%5BTitle%2FAbstract%5D'
    main()
    print('Data saved...\n')
