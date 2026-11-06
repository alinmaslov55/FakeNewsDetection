export interface SampleArticle {
  id: string
  label: string
  type: 'text' | 'url'
  title: string
  content: string
  description: string
}

export const SAMPLE_ARTICLES: SampleArticle[] = [
  {
    id: 'credible-text',
    label: 'Credible Dispatch',
    type: 'text',
    title: 'Global Renewable Energy Expansion',
    content:
      'The International Energy Agency reported on Thursday that global additions of renewable energy capacity increased by fifty percent over the past twelve months. Solar photovoltaic systems accounted for three-quarters of the worldwide expansion, driven by policy incentives and declining hardware manufacturing costs across European and Asian markets.',
    description: 'Factual journalistic report with formal attribution and measured tone.',
  },
  {
    id: 'sensational-text',
    label: 'Sensational Claim',
    type: 'text',
    title: 'Secret Miracle Elixir',
    content:
      'SHOCKING DISCOVERY: Greedy global elites and mainstream doctors have been hiding this ONE weird kitchen spice that instantly cures every chronic illness known to mankind overnight! Big pharma does NOT want you to see this leaked video before it gets deleted from the internet forever!',
    description: 'Sensationalist text with clickbait phrasing, urgency cues, and unsubstantiated claims.',
  },
  {
    id: 'sample-url',
    label: 'Live News Link',
    type: 'url',
    title: 'BBC Tech Article',
    content: 'https://www.bbc.com/news/technology-68524410',
    description: 'Sample live news URL to test BeautifulSoup web scraper.',
  },
]
