#!/usr/bin/env python3
"""
数据库迁移执行脚本
用于执行微信账号关联表的创建和清理重复字段
"""

import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_db_config():
    """获取数据库配置"""
    return {
        'host': os.getenv('POSTGRES_HOST', '192.168.1.7'),
        'port': os.getenv('POSTGRES_PORT', '5433'),
        'database': os.getenv('POSTGRES_DB', 'daoyou'),
        'user': os.getenv('POSTGRES_USER', 'daoyou_user'),
        'password': os.getenv('POSTGRES_PASSWORD', '1013966037zhy')
    }

def run_migration_file(cursor, migration_file: str, description: str) -> bool:
    """执行单个迁移文件"""
    try:
        if not os.path.exists(migration_file):
            print(f"❌ 迁移文件不存在: {migration_file}")
            return False
        
        print(f"📝 正在执行: {description}")
        print(f"   文件: {migration_file}")
        
        with open(migration_file, 'r', encoding='utf-8') as f:
            migration_sql = f.read()
        
        # 执行迁移
        cursor.execute(migration_sql)
        print(f"✅ {description} 执行成功！")
        return True
        
    except Exception as e:
        print(f"❌ {description} 执行失败: {str(e)}")
        return False

def run_migrations():
    """执行所有数据库迁移"""
    config = get_db_config()
    
    try:
        # 连接数据库
        print(f"🔗 正在连接数据库: {config['host']}:{config['port']}/{config['database']}")
        conn = psycopg2.connect(**config)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        print("✅ 数据库连接成功！")
        
        # 迁移文件列表
        migrations = [
            {
                'file': 'V1.0.2__create_wechat_accounts_table.sql',
                'description': '创建微信账号关联表'
            }
        ]
        
        # 执行所有迁移
        success_count = 0
        for migration in migrations:
            migration_file = os.path.join(
                os.path.dirname(__file__), '..', 'migrations', migration['file']
            )
            
            if run_migration_file(cursor, migration_file, migration['description']):
                success_count += 1
        
        print(f"\n📊 迁移结果: {success_count}/{len(migrations)} 成功")
        
        if success_count == len(migrations):
            # 验证表是否创建成功
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'wechat_accounts'
            """)
            
            if cursor.fetchone():
                print("✅ 微信账号关联表创建成功！")
            else:
                print("❌ 微信账号关联表创建失败！")
                return False
            
            # 显示表结构
            cursor.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = 'wechat_accounts'
                ORDER BY ordinal_position
            """)
            
            columns = cursor.fetchall()
            print("\n📋 微信账号关联表结构:")
            print(f"{'字段名':<20} {'数据类型':<20} {'允许空值':<10} {'默认值'}")
            print("-" * 70)
            for col in columns:
                print(f"{col[0]:<20} {col[1]:<20} {col[2]:<10} {col[3] or '无'}")
            
            # 显示用户表结构
            cursor.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = 'users'
                ORDER BY ordinal_position
            """)
            
            user_columns = cursor.fetchall()
            print("\n📋 用户表结构:")
            print(f"{'字段名':<20} {'数据类型':<20} {'允许空值':<10} {'默认值'}")
            print("-" * 70)
            for col in user_columns:
                print(f"{col[0]:<20} {col[1]:<20} {col[2]:<10} {col[3] or '无'}")
        
        cursor.close()
        conn.close()
        
        if success_count == len(migrations):
            print("\n🎉 所有数据库迁移完成！")
            return True
        else:
            print(f"\n⚠️  部分迁移失败，成功: {success_count}/{len(migrations)}")
            return False
        
    except Exception as e:
        print(f"❌ 迁移执行失败: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 开始执行数据库迁移...")
    print("=" * 60)
    success = run_migrations()
    
    if success:
        print("\n✅ 迁移成功！现在可以测试新的微信登录功能了。")
        print("\n📝 主要变更:")
        print("   • 创建了 wechat_accounts 从表")
        print("   • 清理了用户表中的重复微信字段")
        print("   • 实现了微信账号与用户的关联管理")
        sys.exit(0)
    else:
        print("\n❌ 迁移失败！请检查错误信息。")
        sys.exit(1) 