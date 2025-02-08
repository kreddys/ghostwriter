SELECT * FROM pg_available_extensions;

CREATE EXTENSION "uuid-ossp";

SELECT * FROM pg_extension WHERE extname = 'vector';

INSERT INTO test_embeddings (embedding) VALUES ('[0.1, 0.2, 0.3]');

SELECT * FROM post_embeddings;

SELECT *
	FROM post_embeddings;

	--678456726531ef00018d490b,678456726531ef00018d490b,674e64e94a35730001344f94,6745771ca0aa310001220d18,6745771ca0aa310001220d12

ALTER TABLE public.post_embeddings 
ADD COLUMN created_at TIMESTAMP DEFAULT NOW(),
ADD COLUMN updated_at TIMESTAMP DEFAULT NOW();

UPDATE public.post_embeddings 
SET created_at = NOW(), updated_at = NOW();


CREATE TABLE public.post_sources (
  id SERIAL PRIMARY KEY,
  title TEXT NOT NULL,
  source_url TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

select * from public.post_sources;

delete from public.post_sources where id = '364c60ae-1166-4738-a37a-20e9909bc0d6'

ALTER TABLE post_sources 
ADD COLUMN IF NOT EXISTS published_url TEXT NULL;





