-- 创建服务类型表
CREATE TABLE IF NOT EXISTS service_types (
    id UUID PRIMARY KEY,
    key VARCHAR(50) UNIQUE NOT NULL,
    title VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    icon_name VARCHAR(50) NOT NULL,
    color VARCHAR(20) NOT NULL,
    gradient VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 创建更新时间触发器
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 应用触发器到服务类型表
DROP TRIGGER IF EXISTS set_service_types_updated_at ON service_types;
CREATE TRIGGER set_service_types_updated_at
BEFORE UPDATE ON service_types
FOR EACH ROW
EXECUTE FUNCTION update_modified_column();