-- ===================== RESET（谨慎执行）====================
-- 为了便于结构调整与重复导入，这里提供一键重置语句：
-- 执行后会删除本脚本涉及的所有表及触发器函数。
-- 建议仅在开发/测试环境使用，生产环境请按变更脚本执行。

-- 1) 先删除依赖对象（引用关系/向量/解释/条文/案例），最后删除法典
DROP TABLE IF EXISTS citations CASCADE;
DROP TABLE IF EXISTS article_embeddings CASCADE;
DROP TABLE IF EXISTS interpretations CASCADE;
DROP TABLE IF EXISTS articles CASCADE;
DROP TABLE IF EXISTS cases CASCADE;
DROP TABLE IF EXISTS statutes CASCADE;

-- 2) 删除触发器函数（若仍存在）
DROP FUNCTION IF EXISTS trg_articles_tsv_upd() CASCADE;
DROP FUNCTION IF EXISTS trg_interps_tsv_upd() CASCADE;

-- =================== 以上为重置语句 END ====================

-- PostgreSQL 法规库建表脚本（民法典/合同编等）
-- 依赖扩展（按需安装）
CREATE EXTENSION IF NOT EXISTS "pgcrypto";        -- 提供 gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS "pg_trgm";         -- 相似/模糊匹配

-- 可选：pgvector 扩展（若未安装，将跳过向量相关对象）
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'vector') THEN
    CREATE EXTENSION IF NOT EXISTS "vector";      -- 向量检索（pgvector）
  ELSE
    RAISE NOTICE 'pgvector not installed; skip vector features';
  END IF;
END
$$;

-- 1) 法典/法规表
CREATE TABLE IF NOT EXISTS statutes (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  code            TEXT NOT NULL,                 -- 唯一代码，如 civil_code / contract_code
  name            TEXT NOT NULL,                 -- 中文名称，如 民法典 / 合同编
  jurisdiction    TEXT NOT NULL DEFAULT 'PRC',   -- 司法辖区
  version         TEXT NOT NULL DEFAULT '',      -- 版本标识，如 2020（为空表示“未标明版本”）
  effective_from  DATE,
  effective_to    DATE,
  is_valid        BOOLEAN NOT NULL DEFAULT TRUE, -- 当前是否有效
  created_at      TIMESTAMP NOT NULL DEFAULT now(),
  CONSTRAINT statutes_code_version_uk UNIQUE (code, version)
);

-- 2) 条文表（按“条”为粒度）
CREATE TABLE IF NOT EXISTS articles (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  statute_id   UUID NOT NULL REFERENCES statutes(id) ON DELETE CASCADE,
  article_no   TEXT NOT NULL,              -- 原文编号，如 “第七百九十五条”
  title        TEXT,                       -- 可选的小标题
  text         TEXT NOT NULL,              -- 条文全文
  summary      TEXT,                       -- 关键句/摘要（可选）
  keywords     JSONB DEFAULT '[]',         -- 关键词（可选）
  tsv          tsvector,                   -- 全文索引字段（触发器维护）
  created_at   TIMESTAMP NOT NULL DEFAULT now(),
  CONSTRAINT articles_statute_no_uk UNIQUE (statute_id, article_no)
);

CREATE INDEX IF NOT EXISTS idx_articles_statute_no ON articles(statute_id, article_no);
CREATE INDEX IF NOT EXISTS idx_articles_tsv        ON articles USING GIN (tsv);
CREATE INDEX IF NOT EXISTS idx_articles_summary_trgm ON articles USING GIN (summary gin_trgm_ops);

-- 维护 articles.tsv 的触发器
CREATE OR REPLACE FUNCTION trg_articles_tsv_upd() RETURNS trigger AS $$
BEGIN
  NEW.tsv := to_tsvector('simple', COALESCE(NEW.text, ''));
  RETURN NEW;
END
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_articles_tsv ON articles;
CREATE TRIGGER trg_articles_tsv
BEFORE INSERT OR UPDATE OF text
ON articles
FOR EACH ROW
EXECUTE FUNCTION trg_articles_tsv_upd();

-- 3) 司法解释/审理要点（可选）
CREATE TABLE IF NOT EXISTS interpretations (
  id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  related_article_id UUID REFERENCES articles(id) ON DELETE SET NULL,
  title              TEXT,
  text               TEXT NOT NULL,
  tsv                tsvector,                      -- 全文索引字段（触发器维护）
  created_at         TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_interpretations_article ON interpretations(related_article_id);
CREATE INDEX IF NOT EXISTS idx_interpretations_tsv     ON interpretations USING GIN (tsv);

-- 维护 interpretations.tsv 的触发器
CREATE OR REPLACE FUNCTION trg_interps_tsv_upd() RETURNS trigger AS $$
BEGIN
  NEW.tsv := to_tsvector('simple', COALESCE(NEW.text, ''));
  RETURN NEW;
END
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_interps_tsv ON interpretations;
CREATE TRIGGER trg_interps_tsv
BEFORE INSERT OR UPDATE OF text
ON interpretations
FOR EACH ROW
EXECUTE FUNCTION trg_interps_tsv_upd();

-- 4) 裁判案例（仅元数据/要旨，全文不入库）
CREATE TABLE IF NOT EXISTS cases (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  docket_no        TEXT NOT NULL,       -- 案号/外部唯一编号
  title            TEXT,
  court            TEXT,                -- 法院名称（对齐导入器）
  court_level      TEXT,                -- 最高院/高院/中院/基层/专门法院
  cause            TEXT,                -- 案由
  decision_date    DATE,
  decision_type    TEXT,                -- 判决/裁定/指导性案例 等
  jurisdiction     TEXT DEFAULT 'PRC',
  holding          TEXT,                -- 要旨/结论
  summary          TEXT,                -- 摘要（可选）
  keywords         JSONB DEFAULT '[]'::jsonb, -- 关键词（数组）
  external_uri     TEXT,                -- 全文外链（对象存储/文件路径）
  external_sha256  TEXT,                -- 校验
  bytes_length     BIGINT,              -- 文件大小
  created_at       TIMESTAMP NOT NULL DEFAULT now(),
  updated_at       TIMESTAMP NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS cases_docket_no_uk ON cases(docket_no);
CREATE INDEX IF NOT EXISTS idx_cases_date            ON cases(decision_date);
CREATE INDEX IF NOT EXISTS idx_cases_cause_trgm      ON cases USING GIN (cause gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_cases_title_trgm      ON cases USING GIN (title gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_cases_holding_trgm    ON cases USING GIN (holding gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_cases_summary_trgm    ON cases USING GIN (summary gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_cases_keywords_gin    ON cases USING GIN (keywords);

-- 5) 统一引用关系（法条/解释/案例之间的引用/参考）
-- source_type/target_type ∈ {'article','interpretation','case'}
CREATE TABLE IF NOT EXISTS citations (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_type   TEXT NOT NULL,
  source_id     UUID NOT NULL,
  target_type   TEXT NOT NULL,
  target_id     UUID NOT NULL,
  citation_text TEXT,
  confidence    NUMERIC(5,4),          -- 0~1 置信度（可选）
  created_at    TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_citations_source ON citations(source_type, source_id);
CREATE INDEX IF NOT EXISTS idx_citations_target ON citations(target_type, target_id);

-- 6) 条文向量表（用于语义检索；维度按所选嵌入模型调整）
-- 例如 bge-m3: 1024 维；OpenAI text-embedding-3-small: 1536 维
-- 请将 1024 替换为你的实际维度
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'vector') THEN
    CREATE TABLE IF NOT EXISTS article_embeddings (
      article_id UUID PRIMARY KEY REFERENCES articles(id) ON DELETE CASCADE,
      embedding  vector(1024)  -- TODO: 按实际嵌入维度修改
    );

    -- ivfflat 索引（创建前建议：SET enable_seqscan = off; 并先 ANALYZE）
    -- 注意：ivfflat 需要设置合适的 lists 参数，示例 100
    DROP INDEX IF EXISTS idx_article_embeddings_ivfflat;
    CREATE INDEX idx_article_embeddings_ivfflat
    ON article_embeddings
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
  ELSE
    RAISE NOTICE 'pgvector not installed; skipped table article_embeddings and ivfflat index';
  END IF;
END
$$;

-- 7) 常用查询优化（可选）
-- 模糊匹配 article_no
CREATE INDEX IF NOT EXISTS idx_articles_no_trgm ON articles USING GIN (article_no gin_trgm_ops);
-- 按有效法典过滤
CREATE INDEX IF NOT EXISTS idx_statutes_valid ON statutes (is_valid);

-- 8) 示例：插入四大法典元数据（按需执行）
-- INSERT INTO statutes(code, name, version, effective_from, is_valid)
-- VALUES ('civil_code','民法典','2020','2021-01-01', true)
-- ON CONFLICT (code, version) DO NOTHING;

-- 示例：重点法规（民法典 + 民事诉讼法 + 劳动法 + 劳动合同法）一次写入
-- INSERT INTO statutes (code,name,jurisdiction,version,effective_from,is_valid) VALUES
-- ('civil_code','中华人民共和国民法典','PRC','2020','2021-01-01', true),
-- ('civil_procedure_law','中华人民共和国民事诉讼法','PRC','最新',NULL, true),
-- ('labor_law','中华人民共和国劳动法','PRC','最新',NULL, true),
-- ('labor_contract_law','中华人民共和国劳动合同法','PRC','最新',NULL, true),
-- ('labor_contract_law_provision','中华人民共和国劳动合同法实施条例','PRC','最新',NULL, true),
-- ('labor_arbitration_law','中华人民共和国劳动争议调解仲裁法','PRC','最新',NULL, true)
-- ON CONFLICT (code, version) DO NOTHING;
-- 注：原《中华人民共和国婚姻法》已被民法典吸收，相关内容位于民法典“婚姻家庭编”，可在导入条文时以
-- civil_code 作为 statute_code，并在上游数据中记录所属编/章信息用于细分检索与展示。

-- 9) 使用说明
-- - 导入条文时仅需写入 articles(text, article_no, statute_id)，tsv 由触发器自动维护。
-- - 向量嵌入：业务层批量生成 embedding 后写入 article_embeddings(article_id, embedding)。
-- - 检索：推荐“向量 TopN + 全文 ranks 复排”的混合策略。

-- 导入建议（以 CSV 为例，psql 下执行）：
-- CREATE TEMP TABLE import_articles(statute_code TEXT, article_no TEXT, title TEXT, text TEXT, summary TEXT);
-- \COPY import_articles FROM '/path/to/contract_code.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
-- INSERT INTO articles (statute_id, article_no, title, text, summary)
-- SELECT s.id, ia.article_no, NULLIF(ia.title,''), ia.text, ia.summary
-- FROM import_articles ia JOIN statutes s ON s.code = ia.statute_code;
-- ANALYZE articles;

-- 词法检索示例（articles）：
-- WITH q AS (SELECT plainto_tsquery(:q) AS tsq, :q AS kw)
-- SELECT a.id, s.code AS statute_code, s.name AS statute_name, a.article_no,
--        ts_headline('simple', a.text, q.tsq, 'MaxFragments=1, MinWords=5, MaxWords=20') AS snippet,
--        (ts_rank_cd(a.tsv, q.tsq) * 0.8 + COALESCE(similarity(a.summary, q.kw), 0) * 0.2) AS score
-- FROM articles a
-- JOIN statutes s ON s.id = a.statute_id
-- JOIN q ON TRUE
-- WHERE (a.tsv @@ q.tsq OR a.summary ILIKE CONCAT('%%', q.kw, '%%'))
--   AND (:domains IS NULL OR s.code = ANY(:domains))
-- ORDER BY score DESC, a.article_no ASC
-- LIMIT :limit;

-- 8.1) 常见法律/规章/规则 批量 UPSERT（按需执行）
-- 说明：下列为你列出的典型法/规/规则。司法解释类不在此处入库（见“10) 解释导入建议”）。
-- 注意：如需精确生效日期，请在了解后补充 effective_from；version 可用具体年份或“最新”。
-- INSERT INTO statutes (code,name,jurisdiction,version,effective_from,is_valid) VALUES
-- ('patent_law','中华人民共和国专利法','PRC','最新',NULL, true),
-- ('patent_regulation','中华人民共和国专利法实施细则','PRC','最新',NULL, true),
-- ('enterprise_bankruptcy_law','中华人民共和国企业破产法','PRC','最新',NULL, true),
-- ('insurance_law','中华人民共和国保险法','PRC','最新',NULL, true),
-- ('company_law','中华人民共和国公司法','PRC','最新',NULL, true),
-- ('criminal_law','中华人民共和国刑法','PRC','2020',NULL, true),
-- ('constitution','中华人民共和国宪法','PRC','最新',NULL, true),
-- ('consumer_protection_law','中华人民共和国消费者权益保护法','PRC','最新',NULL, true),
-- ('administrative_litigation_law','中华人民共和国行政诉讼法','PRC','最新',NULL, true),
-- ('procuratorate_criminal_procedure_rules','人民检察院刑事诉讼规则','PRC','最新',NULL, true),
-- ('criminal_illegal_evidence_exclusion_provisions','关于办理刑事案件严格排除非法证据若干问题的规定','PRC','最新',NULL, true)
-- ON CONFLICT (code, version) DO NOTHING;

-- 解释/规定类（示例）：以下文档建议作为 interpretations 导入而非 statutes：
-- - 最高人民法院关于适用《中华人民共和国民事诉讼法》的解释(2022)
-- - 民事诉讼证据的若干规定
-- - 审判监督程序若干问题的解释
-- - 执行程序若干问题的解释
-- - （如有）中华人民共和国行政诉讼法的解释

-- 10) 解释导入建议（interpretations）
-- 处理原则：
-- - “实施细则/条例/规章/规则”通常作为独立法规范入库（statutes + articles）。
-- - “司法解释/若干问题的解释/证据规定”等作为 interpretations 入库。
--   - 若能精确到对应条文，填充 related_article_no 并对齐到 articles.id；
--   - 若仅为整部解释文本或章节级，related_article_no 置空，后续再做细粒度对齐。
-- 导入示例（psql 会话）：
-- CREATE TEMP TABLE import_interpretations(
--   statute_code        TEXT,              -- 被解释的法典 code，例如 'civil_procedure_law'
--   related_article_no  TEXT NULL,         -- 可选：对应条号，如“第六十三条”；为空表示整部/章节
--   title               TEXT,
--   text                TEXT               -- 解释全文（按条/款拆分后的粒度）
-- );
-- \COPY import_interpretations FROM '/path/to/cpl_interpretation_2022.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
-- INSERT INTO interpretations(related_article_id, title, text)
-- SELECT a.id, ii.title, ii.text
-- FROM import_interpretations ii
-- LEFT JOIN statutes s ON s.code = ii.statute_code
-- LEFT JOIN articles a  ON a.statute_id = s.id AND (ii.related_article_no IS NOT NULL AND a.article_no = ii.related_article_no);
-- -- 未对齐条文的（a.id 为空），也可先插入一条 interpretations，后续再补齐关联：
-- INSERT INTO interpretations(related_article_id, title, text)
-- SELECT NULL, ii.title, ii.text FROM import_interpretations ii WHERE ii.related_article_no IS NULL;
-- ANALYZE interpretations;
-- ANALYZE interpretations;

-- 11) AI RAG 辅助：主题词库 / 标签词库 / 法条要件库 / 主题→法条映射
-- 用于在业务层将“临时关键词”升级为“结构化增强”，支持可持续扩展与重排打分

-- 11.1 主题词库（覆盖 民/刑/行/仲裁/执行 及常见主题，如 民间借贷/诈骗/劳动争议/离婚 等）
CREATE TABLE IF NOT EXISTS ai_legal_taxonomy (
  id          SERIAL PRIMARY KEY,
  topic_key   TEXT UNIQUE,          -- 主题键，如 "民间借贷"、"诈骗"、"劳动争议"
  case_nature TEXT,                 -- 民/刑/行/仲裁/执行/非诉
  causes      JSONB,                -- 民事案由列表（可空）
  charges     JSONB,                -- 罪名列表（可空）
  keywords    JSONB,                -- 主题关键词（数组）
  synonyms    JSONB,                -- 同义/别名（数组）
  domains     JSONB,                -- 关联法规域，如 ["civil_code","contract_code"]
  examples    JSONB,                -- 示例句/典型事实（数组）
  created_at  TIMESTAMP NOT NULL DEFAULT now(),
  updated_at  TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ai_legal_taxonomy_keywords_gin ON ai_legal_taxonomy USING GIN (keywords);
CREATE INDEX IF NOT EXISTS idx_ai_legal_taxonomy_synonyms_gin ON ai_legal_taxonomy USING GIN (synonyms);
CREATE INDEX IF NOT EXISTS idx_ai_legal_taxonomy_domains_gin  ON ai_legal_taxonomy USING GIN (domains);

-- 11.2 标签词库（如 高利息/违约金/证据保全/仲裁协议/诉讼时效 等）
CREATE TABLE IF NOT EXISTS ai_law_terms (
  id         SERIAL PRIMARY KEY,
  term       TEXT UNIQUE,
  synonyms   JSONB,                -- 同义词数组
  domains    JSONB,                -- 领域数组
  created_at TIMESTAMP NOT NULL DEFAULT now(),
  updated_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ai_law_terms_synonyms_gin ON ai_law_terms USING GIN (synonyms);
CREATE INDEX IF NOT EXISTS idx_ai_law_terms_domains_gin  ON ai_law_terms USING GIN (domains);

-- 11.3 法条要件库（提炼法条的要件/时效/除斥/期限等）
CREATE TABLE IF NOT EXISTS ai_article_elements (
  id                SERIAL PRIMARY KEY,
  code              TEXT NOT NULL,         -- 法典名，如 "民法典"、"刑法"、"劳动合同法"
  article_no        TEXT NOT NULL,         -- 条号原文，如 "577"
  elements_to_prove JSONB,                 -- 要件清单（数组）
  time_limits       JSONB,                 -- 时效/除斥/期限（数组）
  notes             TEXT,
  created_at        TIMESTAMP NOT NULL DEFAULT now(),
  updated_at        TIMESTAMP NOT NULL DEFAULT now(),
  CONSTRAINT ai_article_elements_code_no_uk UNIQUE (code, article_no)
);

CREATE INDEX IF NOT EXISTS idx_ai_article_elements_elem_gin ON ai_article_elements USING GIN (elements_to_prove);
CREATE INDEX IF NOT EXISTS idx_ai_article_elements_time_gin ON ai_article_elements USING GIN (time_limits);

-- 11.4 主题→法条映射（兜底直连 / 先验权重，支持重排打分）
CREATE TABLE IF NOT EXISTS ai_topic_to_articles (
  id         SERIAL PRIMARY KEY,
  topic_key  TEXT NOT NULL REFERENCES ai_legal_taxonomy(topic_key) ON DELETE CASCADE,
  code       TEXT NOT NULL,
  article_no TEXT NOT NULL,
  weight     NUMERIC DEFAULT 1.0,
  created_at TIMESTAMP NOT NULL DEFAULT now(),
  updated_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ai_topic_to_articles_topic ON ai_topic_to_articles(topic_key);
CREATE INDEX IF NOT EXISTS idx_ai_topic_to_articles_code_no ON ai_topic_to_articles(code, article_no);

-- 12) 重置辅助表（按需执行）
-- 选项 A：仅清空数据并重置自增主键
-- 注意：TRUNCATE 会清空所有数据，请谨慎执行（建议仅用于开发/重建场景）
-- TRUNCATE TABLE ai_topic_to_articles, ai_article_elements, ai_law_terms, ai_legal_taxonomy RESTART IDENTITY CASCADE;

-- 选项 B：彻底删除表结构（随后可重新建表）
-- DROP TABLE IF EXISTS ai_topic_to_articles CASCADE;
-- DROP TABLE IF EXISTS ai_article_elements CASCADE;
-- DROP TABLE IF EXISTS ai_law_terms CASCADE;
-- DROP TABLE IF EXISTS ai_legal_taxonomy CASCADE;

-- 13) Cases 引用关联列（按需执行）
-- 用于记录：
-- - related_index_raw：原始抓取到的条文/解释引用文本（未结构化）
-- - related_citations：结构化后的引用列表（如 [{"code":"民法典","article_no":"577","confidence":0.9}]）
ALTER TABLE cases ADD COLUMN IF NOT EXISTS related_index_raw TEXT;
ALTER TABLE cases ADD COLUMN IF NOT EXISTS related_citations JSONB DEFAULT '[]'::jsonb;