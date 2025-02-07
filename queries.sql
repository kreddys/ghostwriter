SELECT * FROM pg_available_extensions;

CREATE EXTENSION vector;

SELECT * FROM pg_extension WHERE extname = 'vector';

INSERT INTO test_embeddings (embedding) VALUES ('[0.1, 0.2, 0.3]');

SELECT * FROM test_embeddings;

SELECT *
	FROM post_embeddings;

	--678456726531ef00018d490b,678456726531ef00018d490b,674e64e94a35730001344f94,6745771ca0aa310001220d18,6745771ca0aa310001220d12

ALTER TABLE public.post_embeddings 
ADD COLUMN created_at TIMESTAMP DEFAULT NOW(),
ADD COLUMN updated_at TIMESTAMP DEFAULT NOW();

UPDATE public.post_embeddings 
SET created_at = NOW(), updated_at = NOW();







