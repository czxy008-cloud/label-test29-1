-- =====================================================================
-- 在线投票调查系统 数据库 DDL 脚本
-- 数据库: PostgreSQL 12+
-- 说明: 本脚本创建系统所需的全部表结构，包括用户、问卷、问题、选项和投票记录
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. 用户表 (users)
--    存储系统注册用户信息，支持JWT令牌认证
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,                              -- 用户唯一标识，自增主键
    username        VARCHAR(50)  NOT NULL UNIQUE,                    -- 用户名，唯一且不为空
    email           VARCHAR(255) NOT NULL UNIQUE,                    -- 邮箱地址，唯一且不为空
    password_hash   VARCHAR(255) NOT NULL,                           -- 密码哈希值（bcrypt加密存储）
    is_admin        BOOLEAN      NOT NULL DEFAULT FALSE,             -- 是否为管理员，默认普通用户
    created_at      TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP, -- 账户创建时间
    updated_at      TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP  -- 账户最后更新时间
);

-- 为常用查询字段创建索引
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email    ON users(email);

-- ---------------------------------------------------------------------
-- 2. 问卷表 (surveys)
--    存储调查问卷的基本信息和元数据
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS surveys (
    id              SERIAL PRIMARY KEY,                              -- 问卷唯一标识，自增主键
    title           VARCHAR(200) NOT NULL,                           -- 问卷标题
    description     TEXT,                                             -- 问卷描述/说明文字
    creator_id      INTEGER      NOT NULL REFERENCES users(id) ON DELETE CASCADE, -- 创建者ID，外键关联users表
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE,              -- 问卷是否处于激活状态
    share_token     VARCHAR(64)  NOT NULL UNIQUE,                    -- 分享令牌，用于生成唯一分享链接
    expire_at       TIMESTAMP,                                        -- 问卷过期时间（NULL表示永不过期）
    created_at      TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP, -- 问卷创建时间
    updated_at      TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP  -- 问卷最后更新时间
);

-- 为常用查询字段创建索引
CREATE INDEX IF NOT EXISTS idx_surveys_creator_id  ON surveys(creator_id);
CREATE INDEX IF NOT EXISTS idx_surveys_share_token ON surveys(share_token);
CREATE INDEX IF NOT EXISTS idx_surveys_is_active   ON surveys(is_active);

-- ---------------------------------------------------------------------
-- 3. 问题表 (questions)
--    存储问卷中的问题信息，支持单选、多选、填空三种题型
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS questions (
    id              SERIAL PRIMARY KEY,                              -- 问题唯一标识，自增主键
    survey_id       INTEGER      NOT NULL REFERENCES surveys(id) ON DELETE CASCADE, -- 所属问卷ID，外键关联surveys表
    question_text   VARCHAR(500) NOT NULL,                           -- 问题文本内容
    question_type   VARCHAR(20)  NOT NULL,                           -- 问题类型: single_choice(单选) / multiple_choice(多选) / text_input(填空)
    is_required     BOOLEAN      NOT NULL DEFAULT TRUE,              -- 是否为必答题
    sort_order      INTEGER      NOT NULL DEFAULT 0,                 -- 问题在问卷中的排序序号
    created_at      TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP  -- 问题创建时间
);

-- 为常用查询字段创建索引
CREATE INDEX IF NOT EXISTS idx_questions_survey_id ON questions(survey_id);

-- question_type 的约束检查
ALTER TABLE questions ADD CONSTRAINT chk_question_type
    CHECK (question_type IN ('single_choice', 'multiple_choice', 'text_input'));

-- ---------------------------------------------------------------------
-- 4. 选项表 (options)
--    存储单选题和多选题的选项内容
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS options (
    id              SERIAL PRIMARY KEY,                              -- 选项唯一标识，自增主键
    question_id     INTEGER      NOT NULL REFERENCES questions(id) ON DELETE CASCADE, -- 所属问题ID，外键关联questions表
    option_text     VARCHAR(500) NOT NULL,                           -- 选项文本内容
    sort_order      INTEGER      NOT NULL DEFAULT 0,                 -- 选项在问题中的排序序号
    created_at      TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP  -- 选项创建时间
);

-- 为常用查询字段创建索引
CREATE INDEX IF NOT EXISTS idx_options_question_id ON options(question_id);

-- ---------------------------------------------------------------------
-- 5. 投票表 (votes)
--    存储用户的投票记录
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS votes (
    id              SERIAL PRIMARY KEY,                              -- 投票记录唯一标识，自增主键
    survey_id       INTEGER      NOT NULL REFERENCES surveys(id) ON DELETE CASCADE,   -- 所属问卷ID
    question_id     INTEGER      NOT NULL REFERENCES questions(id) ON DELETE CASCADE, -- 所属问题ID
    option_id       INTEGER      REFERENCES options(id) ON DELETE CASCADE,            -- 选中的选项ID（填空题为NULL）
    text_value      TEXT,                                             -- 填空题的文本值（选择题为NULL）
    voter_session   VARCHAR(100) NOT NULL,                            -- 投票者会话标识（用于匿名投票去重）
    voter_id        INTEGER      REFERENCES users(id) ON DELETE SET NULL,            -- 登录用户ID（匿名投票为NULL）
    status          VARCHAR(20)  NOT NULL DEFAULT 'submitted',        -- 投票状态: draft(草稿)/submitted(已提交)
    voted_at        TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP  -- 投票时间
);

-- 为常用查询字段创建索引
CREATE INDEX IF NOT EXISTS idx_votes_survey_id    ON votes(survey_id);
CREATE INDEX IF NOT EXISTS idx_votes_question_id  ON votes(question_id);
CREATE INDEX IF NOT EXISTS idx_votes_option_id    ON votes(option_id);
CREATE INDEX IF NOT EXISTS idx_votes_voter_id     ON votes(voter_id);
CREATE INDEX IF NOT EXISTS idx_votes_status       ON votes(status);

-- status 的约束检查
ALTER TABLE votes ADD CONSTRAINT chk_vote_status
    CHECK (status IN ('draft', 'submitted'));

-- =====================================================================
-- 触发器：自动更新 updated_at 字段
-- =====================================================================

-- 创建通用的更新时间戳触发器函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 为 users 表添加更新时间戳触发器
DROP TRIGGER IF EXISTS trg_users_updated_at ON users;
CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 为 surveys 表添加更新时间戳触发器
DROP TRIGGER IF EXISTS trg_surveys_updated_at ON surveys;
CREATE TRIGGER trg_surveys_updated_at
    BEFORE UPDATE ON surveys
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
