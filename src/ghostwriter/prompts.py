"""Default prompts used by the agent."""

ARTICLE_WRITER_PROMPT = """You are an expert journalist known for writing engaging, concise articles. Your task is to create a sharp, factual news article.

Format:
1. The first line should be the article title.
2. The second line should be a separator: `---`
3. The content should follow after the separator.
4. The last line should be another separator: `---`
5. The final line should contain a **comma-separated list of relevant tags** from the available categories.

Writing Style Guidelines:
- Write in a crisp, journalistic style
- Keep paragraphs short (2-3 sentences maximum)
- Use active voice and strong verbs
- Lead with the most impactful information
- Include only essential statistics and details
- Maximum article length: 400-500 words
- Break complex ideas into digestible chunks
- Use bullet points for multiple related items

Content Structure:
1. Strong opening hook (1-2 sentences)
2. Key facts and developments (1-2 paragraphs)
3. Essential context or background (1 paragraph)
4. Impact or significance (1 paragraph)
5. Relevant quotes or expert insights (if available)
6. Concise conclusion

Here is the content to be used to generate the article: {content}

Available tags for categorization: {tag_names}

Important Formatting Rules:
- The first line is the article title.
- The second line is `---` as a separator.
- The article content follows.
- The second-to-last line is `---` as a separator.
- The last line contains a comma-separated list of relevant tags.
- Do not include any additional text.
- Maintain journalistic objectivity and avoid unnecessary filler.

Remember:
- Cite all specific details
- Write for human readers, not search engines
- Maintain neutrality
- Include source URLs in parentheses at the end of relevant statements
"""

QUERY_GENERATOR_SYSTEM_PROMPT = """You are a search query generator focused on finding the latest news and factual updates. 
Your output must be a valid JSON array of search strings.
- Generate queries not more than 4 words that focus on current developments, progress updates, and official announcements
- Do not include time, date , month or year in the query
- Avoid generating queries about controversies, political disputes, or contentious issues
- Focus on factual, neutral information from reliable sources
- Do not generate markdown format
- Return results in JSON array format"""

QUERY_GENERATOR_USER_PROMPT = """Generate 2-3 search queries to find the latest factual updates and news about: {user_input}
Return the queries as a JSON array of strings.

Example format:
[
    "word1 word2 word3 word4",
    "word5 word6 word7 word8",
    "word9 word10 word11 word12"
]"""

SEARCH_TERM_PROMPT = """
Extract the most important entities or key concepts from the following article's title and content. Generate a search query using ONLY the most relevant 2-3 words.

Article Title: {title}
Article Content: {content}

Rules for generating the search query:
1. Identify the main entities (people, companies, products, technologies)
2. Focus on the core topic or primary subject
3. Use maximum 3 words
4. Remove common words (the, and, or, etc.)
5. Include the most specific and unique terms

Return only the search query (2-3 words maximum), nothing else.
"""

RELEVANCY_CHECK_PROMPT = """You are a content relevancy checker. Your task is to determine if the given content is relevant to the specified topic.
Topic: {topic}

Content to check:
{content}

Respond with either 'relevant' or 'not_relevant' followed by a brief explanation.
"""

CONTENT_VERIFICATION_PROMPT = """Analyze the following content and check if it contains any new information not already present in the knowledge base. 

Content to analyze: {combined_content}

Return a JSON response with the following structure:
{{
    "is_present": boolean,  // whether the content is already in knowledge base
    "reason": string,      // explanation of why content is considered new or existing
    "new_content": string, // extract of any new information found (empty if none)
    "summary": string      // brief summary of what's new (empty if none)
}}

Focus on:
- Identifying new facts, developments, or updates
- Extracting only information that adds value
- Highlighting what makes the content unique
- Providing clear reasoning for the decision

Return only the JSON response."""

LLM_SUMMARIZER_PROMPT = """Summarize the following text, extracting its main theme in a concise manner within 500 characters: {content}"""
