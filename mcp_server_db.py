import json
from mcp.server.fastmcp import FastMCP
from sqlalchemy import create_engine, inspect, text

# DB 연결 카탈로그
with open('connections.json', 'r', encoding='utf-8') as f:
    DB_CONNECTIONS = json.load(f)

mcp = FastMCP("DatabaseMCP")

def detect_db_type(url: str) -> str:
    """데이터베이스 타입 감지"""
    if 'oracle' in url or 'oracledb' in url:
        return 'Oracle'
    elif 'mysql' in url:
        return 'MySQL'
    elif 'postgresql' in url:
        return 'PostgreSQL'
    elif 'sqlite' in url:
        return 'SQLite'
    elif 'mssql' in url or 'pymssql' in url:
        return 'SQLServer'
    return 'Unknown'

# Tool 1: 데이터베이스 목록
@mcp.tool()
async def list_databases() -> str:
    """Show all available databases"""
    if not DB_CONNECTIONS:
        return "No databases found"
    
    result = "📊 Available databases:\n\n"
    for idx, (name, info) in enumerate(DB_CONNECTIONS.items(), 1):
        result += f"{idx}. {name}\n"
        result += f"   📝 {info['description']}\n\n"
    return result


# Tool 2: 테이블 목록 (데이터 개수 포함)
@mcp.tool()
async def list_tables(database: str) -> str:
    """Show all tables in database with row counts"""
    if database not in DB_CONNECTIONS:
        return f"Database '{database}' not found"
    
    try:
        engine = create_engine(DB_CONNECTIONS[database]["url"])
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        if not tables:
            return f"No tables found in {database}"
        
        result = f"📊 Tables in '{database}' database:\n\n"
        
        for idx, table in enumerate(tables, 1):
            try:
                with engine.connect() as conn:
                    count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                    result += f"{idx}. {table}: {count:,} records\n"
            except:
                result += f"{idx}. {table}\n"
        
        #result += f"\n💡 Use 'show_data' to view actual data from any table"
        return result
        
    except Exception as e:
        return f"Error accessing database: {str(e)}"


# Tool 3: 데이터 보기
@mcp.tool()
async def show_data(database: str, table: str, limit: int) -> str:
    """Show actual data from table"""
    if database not in DB_CONNECTIONS:
        return f"Database '{database}' not found"
    
    # 기본값 및 제한
    if limit <= 0:
        limit = 10
    if limit > 100:
        limit = 100
    
    try:
        db_url = DB_CONNECTIONS[database]["url"]
        engine = create_engine(db_url)
        
        # DB 타입 감지 (중요!)
        db_type = detect_db_type(db_url)
        
        with engine.connect() as conn:
            # 전체 개수 확인
            total = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            
            # DB별 다른 쿼리 사용
            if db_type == 'Oracle':
                query = text(f"SELECT * FROM {table} WHERE ROWNUM <= :limit")
                result = conn.execute(query, {"limit": limit})
            elif db_type == 'SQLServer':
                query = text(f"SELECT TOP {limit} * FROM {table}")
                result = conn.execute(query)  # SQL Server는 파라미터 없이
            else:  # MySQL, PostgreSQL, SQLite
                query = text(f"SELECT * FROM {table} LIMIT :limit")
                result = conn.execute(query, {"limit": limit})
            
            data = result.fetchall()
            headers = list(result.keys())
            
            if not data:
                return f"The table '{table}' is empty (no data)"
            
            # 사용자 친화적 출력
            output = f"📊 Data from '{table}' table:\n"
            output += f"📌 Showing {len(data)} of {total:,} total records\n\n"
            
            # 컬럼 헤더
            output += " | ".join(headers) + "\n"
            output += "=" * 60 + "\n"
            
            # 실제 데이터
            for row in data:
                row_values = []
                for val in row:
                    if val is None:
                        row_values.append("-")
                    elif isinstance(val, (int, float)):
                        row_values.append(str(val))
                    else:
                        str_val = str(val)
                        if len(str_val) > 30:
                            str_val = str_val[:27] + "..."
                        row_values.append(str_val)
                
                output += " | ".join(row_values) + "\n"
            
            if total > limit:
                output += f"\n더 많은 데이터를 보려면 말씀해주세요"
            
            return output
            
    except Exception as e:
        return f"Error reading data: {str(e)}"


# Tool 4: 데이터 검색/필터링
@mcp.tool()
async def search_data(database: str, table: str, column: str, value: str) -> str:
    """Search for specific data in table"""
    if database not in DB_CONNECTIONS:
        return f"Database '{database}' not found"
    
    try:
        engine = create_engine(DB_CONNECTIONS[database]["url"])
        
        with engine.connect() as conn:
            # 검색 쿼리 (LIKE 사용)
            query = text(f"""
                SELECT * FROM {table} 
                WHERE {column} LIKE :search_value 
                LIMIT 20
            """)
            
            # 부분 매칭을 위해 % 추가
            search_pattern = f"%{value}%"
            result = conn.execute(query, {"search_value": search_pattern})
            
            data = result.fetchall()
            headers = list(result.keys())
            
            if not data:
                return f"No results found for '{value}' in column '{column}'"
            
            # 결과 출력
            output = f"🔍 Search Results:\n"
            output += f"📌 Found {len(data)} record(s) where '{column}' contains '{value}'\n\n"
            
            # 헤더
            output += " | ".join(headers) + "\n"
            output += "=" * 60 + "\n"
            
            # 데이터
            for row in data:
                row_values = [str(val) if val is not None else "-" for val in row]
                output += " | ".join(row_values) + "\n"
            
            return output
            
    except Exception as e:
        return f"Search error: {str(e)}"


# Tool 5: 데이터 추가 (INSERT)
@mcp.tool()
async def add_data(database: str, table: str, data: str) -> str:
    """Add new data to table. Format: column1:value1,column2:value2"""
    if database not in DB_CONNECTIONS:
        return f"Database '{database}' not found"
    
    try:
        # 데이터 파싱 (column:value,column:value 형식)
        pairs = data.split(',')
        columns = []
        values = []
        
        for pair in pairs:
            if ':' not in pair:
                return f"Invalid format. Use: column1:value1,column2:value2"
            
            col, val = pair.split(':', 1)
            columns.append(col.strip())
            values.append(val.strip())
        
        # SQL 생성
        columns_str = ", ".join(columns)
        placeholders = ", ".join([f":{col}" for col in columns])
        
        insert_sql = f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders})"
        
        engine = create_engine(DB_CONNECTIONS[database]["url"])
        
        with engine.connect() as conn:
            # 트랜잭션 시작
            trans = conn.begin()
            try:
                # 값 딕셔너리 생성
                value_dict = {}
                for col, val in zip(columns, values):
                    # 'NULL' 문자열을 None으로 변환
                    if val.upper() == 'NULL':
                        value_dict[col] = None
                    # 숫자 변환 시도
                    elif val.isdigit():
                        value_dict[col] = int(val)
                    elif val.replace('.', '', 1).isdigit():
                        value_dict[col] = float(val)
                    else:
                        value_dict[col] = val
                
                # INSERT 실행
                conn.execute(text(insert_sql), value_dict)
                trans.commit()
                
                # 성공 메시지
                output = f"✅ Successfully added new record to '{table}'!\n\n"
                output += "Added data:\n"
                for col, val in zip(columns, values):
                    output += f"  • {col}: {val}\n"
                
                # 추가된 데이터 확인
                output += f"\n💡 Use 'show_data' to see the updated table"
                
                return output
                
            except Exception as e:
                trans.rollback()
                return f"❌ Failed to add data: {str(e)}"
                
    except Exception as e:
        return f"Error: {str(e)}"


# Tool 6: 데이터 삭제 (DELETE) - 수정된 버전
@mcp.tool()
async def delete_data(database: str, table: str, condition: str) -> str:
    """Delete data from table. Format: column:value"""
    if database not in DB_CONNECTIONS:
        return f"Database '{database}' not found"
    
    try:
        # 조건 파싱
        if ':' not in condition:
            return "Invalid format. Use: column:value (e.g., id:5)"
        
        column, value = condition.split(':', 1)
        column = column.strip()
        value = value.strip()
        
        engine = create_engine(DB_CONNECTIONS[database]["url"])
        
        # 값 타입 처리
        if value.isdigit():
            typed_value = int(value)
        elif value.replace('.', '', 1).isdigit():
            typed_value = float(value)
        else:
            typed_value = value
        
        # 방법 1: 각각 별도의 connection 사용
        # 먼저 삭제될 데이터 확인
        with engine.connect() as conn:
            check_sql = text(f"SELECT * FROM {table} WHERE {column} = :value")
            result = conn.execute(check_sql, {"value": typed_value})
            to_delete = result.fetchall()
            headers = list(result.keys()) if to_delete else []
        
        if not to_delete:
            return f"No records found with {column} = '{value}'"
        
        # 삭제 확인 메시지
        output = f"⚠️ About to delete {len(to_delete)} record(s):\n\n"
        
        # 삭제될 데이터 미리보기 (최대 5개)
        if headers:
            output += " | ".join(headers) + "\n"
            output += "-" * 50 + "\n"
            
            for row in to_delete[:5]:
                row_str = " | ".join(str(val) if val else "-" for val in row)
                output += row_str + "\n"
            
            if len(to_delete) > 5:
                output += f"... and {len(to_delete) - 5} more records\n"
        
        # 실제 삭제 실행 (새로운 connection과 명시적 트랜잭션)
        with engine.begin() as conn:  # begin()이 자동으로 commit/rollback 처리
            try:
                delete_sql = text(f"DELETE FROM {table} WHERE {column} = :value")
                conn.execute(delete_sql, {"value": typed_value})
                # commit은 자동으로 됨 (with 블록 종료 시)
                
                output += f"\n✅ Successfully deleted {len(to_delete)} record(s) from '{table}'"
                output += f"\n💡 Use 'show_data' to see the updated table"
                
                return output
                
            except Exception as e:
                # rollback도 자동으로 됨 (예외 발생 시)
                return f"❌ Failed to delete: {str(e)}"
                
    except Exception as e:
        return f"Error: {str(e)}"

# Tool 7: 데이터 수정 (UPDATE)
@mcp.tool()
async def update_data(database: str, table: str, set_data: str, condition: str) -> str:
    """Update existing data. Format set_data: col1:val1,col2:val2 condition: col:val"""
    if database not in DB_CONNECTIONS:
        return f"Database '{database}' not found"
    
    try:
        # SET 절 파싱
        set_pairs = set_data.split(',')
        set_parts = []
        set_values = {}
        
        for i, pair in enumerate(set_pairs):
            if ':' not in pair:
                return "Invalid set format. Use: column1:value1,column2:value2"
            
            col, val = pair.split(':', 1)
            col = col.strip()
            val = val.strip()
            
            set_parts.append(f"{col} = :set_{i}")
            
            # 타입 변환
            if val.upper() == 'NULL':
                set_values[f'set_{i}'] = None
            elif val.isdigit():
                set_values[f'set_{i}'] = int(val)
            elif val.replace('.', '', 1).isdigit():
                set_values[f'set_{i}'] = float(val)
            else:
                set_values[f'set_{i}'] = val
        
        # WHERE 절 파싱
        if ':' not in condition:
            return "Invalid condition format. Use: column:value"
        
        cond_col, cond_val = condition.split(':', 1)
        cond_col = cond_col.strip()
        cond_val = cond_val.strip()
        
        # 조건 값 타입 변환
        if cond_val.isdigit():
            typed_cond_val = int(cond_val)
        elif cond_val.replace('.', '', 1).isdigit():
            typed_cond_val = float(cond_val)
        else:
            typed_cond_val = cond_val
        
        engine = create_engine(DB_CONNECTIONS[database]["url"])
        
        # 먼저 영향받을 행 확인
        with engine.connect() as conn:
            check_sql = text(f"SELECT * FROM {table} WHERE {cond_col} = :cond_val")
            result = conn.execute(check_sql, {"cond_val": typed_cond_val})
            affected = result.fetchall()
            
        if not affected:
            return f"No records found with {cond_col} = '{cond_val}'"
        
        # UPDATE 실행
        with engine.begin() as conn:
            set_clause = ", ".join(set_parts)
            update_sql = text(f"UPDATE {table} SET {set_clause} WHERE {cond_col} = :cond_val")
            
            # 모든 파라미터 합치기
            all_params = set_values.copy()
            all_params['cond_val'] = typed_cond_val
            
            conn.execute(update_sql, all_params)
            
            output = f"✅ Successfully updated {len(affected)} record(s) in '{table}'\n\n"
            output += "Updated fields:\n"
            for pair in set_pairs:
                col, val = pair.split(':', 1)
                output += f"  • {col.strip()} → {val.strip()}\n"
            output += f"\nCondition: {cond_col} = {cond_val}\n"
            output += f"💡 Use 'show_data' to see the changes"
            
            return output
            
    except Exception as e:
        return f"Update error: {str(e)}"


# Tool 8: 테이블 조인 (수정된 버전)
@mcp.tool()
async def join_tables(database: str, table1: str, table2: str, join_key: str) -> str:
    """Join two tables to show related data together"""
    if database not in DB_CONNECTIONS:
        return f"Database '{database}' not found"
    
    try:
        engine = create_engine(DB_CONNECTIONS[database]["url"])
        
        with engine.connect() as conn:
            inspector = inspect(engine)
            
            # 각 테이블의 컬럼 가져오기
            cols1 = [col['name'] for col in inspector.get_columns(table1)]
            cols2 = [col['name'] for col in inspector.get_columns(table2)]
            
            # 조인 키 파싱 (여러 형식 지원)
            if '=' in join_key:
                # 형식: "students.course_id=courses.id"
                left_part, right_part = join_key.split('=')
                
                # 테이블명 제거
                if '.' in left_part:
                    left_table, left_key = left_part.strip().split('.')
                else:
                    left_key = left_part.strip()
                    left_table = table1
                
                if '.' in right_part:
                    right_table, right_key = right_part.strip().split('.')
                else:
                    right_key = right_part.strip()
                    right_table = table2
            else:
                # 단순 형식: "id" (양쪽 테이블에 같은 이름의 컬럼이 있다고 가정)
                # 또는 "course_id:id" 형식
                if ':' in join_key:
                    left_key, right_key = join_key.split(':')
                    left_key = left_key.strip()
                    right_key = right_key.strip()
                else:
                    # 자동 매칭 시도 (foreign key 패턴 찾기)
                    left_key = None
                    right_key = None
                    
                    # table1에서 table2_id 패턴 찾기
                    for col in cols1:
                        if col == f"{table2}_id" or col == f"{table2[:-1]}_id":  # courses -> course_id
                            left_key = col
                            right_key = 'id'
                            break
                        elif col == 'id' and f"{table1}_id" in cols2:
                            left_key = 'id'
                            right_key = f"{table1}_id"
                            break
                    
                    if not left_key:
                        # 공통 컬럼 찾기
                        common_cols = set(cols1) & set(cols2)
                        if common_cols:
                            left_key = right_key = list(common_cols)[0]
                        else:
                            return f"❌ Cannot find join columns. Please specify like 'course_id=id' or 'course_id:id'"
            
            # 조인 키 검증
            if left_key not in cols1:
                return f"❌ Column '{left_key}' not found in table '{table1}'\nAvailable columns: {', '.join(cols1)}"
            if right_key not in cols2:
                return f"❌ Column '{right_key}' not found in table '{table2}'\nAvailable columns: {', '.join(cols2)}"
            
            # 조인 타입 결정 (실제 관계 확인)
            # 먼저 INNER JOIN으로 시도
            join_sql = text(f"""
                SELECT 
                    t1.*,
                    t2.*
                FROM {table1} t1
                INNER JOIN {table2} t2 ON t1.{left_key} = t2.{right_key}
                LIMIT 20
            """)
            
            result = conn.execute(join_sql)
            data = result.fetchall()
            headers = list(result.keys())
            
            # 결과가 없으면 LEFT JOIN 시도
            if not data:
                join_sql = text(f"""
                    SELECT 
                        t1.*,
                        t2.*
                    FROM {table1} t1
                    LEFT JOIN {table2} t2 ON t1.{left_key} = t2.{right_key}
                    LIMIT 20
                """)
                
                result = conn.execute(join_sql)
                data = result.fetchall()
                headers = list(result.keys())
                join_type = "LEFT JOIN"
            else:
                join_type = "INNER JOIN"
            
            if not data:
                return f"❌ No data found in '{table1}' or join produced no results"
            
            # 조인 통계
            total_t1 = conn.execute(text(f"SELECT COUNT(*) FROM {table1}")).scalar()
            total_t2 = conn.execute(text(f"SELECT COUNT(*) FROM {table2}")).scalar()
            
            # 결과 출력
            output = f"📊 Join Result: {table1} ⟷ {table2}\n"
            output += f"Join Type: {join_type}\n"
            output += f"Join Condition: {table1}.{left_key} = {table2}.{right_key}\n"
            output += f"Tables: {table1} ({total_t1} rows) + {table2} ({total_t2} rows)\n"
            output += f"Showing {len(data)} joined record(s)\n"
            output += "=" * 80 + "\n\n"
            
            # 헤더 출력 (중복 제거 및 테이블명 표시)
            display_headers = []
            for i, header in enumerate(headers):
                # 어느 테이블에서 온 컬럼인지 표시
                if i < len(cols1):
                    display_headers.append(f"{table1}.{header}")
                else:
                    display_headers.append(f"{table2}.{header}")
            
            # 너무 많은 컬럼이면 주요 컬럼만 표시
            if len(display_headers) > 8:
                # id, name 등 주요 컬럼 우선 표시
                important_cols = []
                for h in display_headers:
                    if any(key in h.lower() for key in ['id', 'name', 'title', 'course', 'student']):
                        important_cols.append(h)
                        if len(important_cols) >= 8:
                            break
                
                if important_cols:
                    display_headers = important_cols[:8]
                else:
                    display_headers = display_headers[:8]
                
                header_indices = [headers.index(h.split('.')[1]) for h in display_headers]
            else:
                header_indices = list(range(len(headers)))
            
            # 헤더 출력
            output += " | ".join([h.split('.')[1] for h in display_headers]) + "\n"
            output += "-" * 80 + "\n"
            
            # 데이터 출력
            for row_num, row in enumerate(data[:10], 1):
                row_values = []
                for idx in header_indices:
                    val = row[idx]
                    if val is None:
                        row_values.append("-")
                    else:
                        str_val = str(val)
                        if len(str_val) > 15:
                            str_val = str_val[:12] + "..."
                        row_values.append(str_val)
                
                output += " | ".join(row_values) + "\n"
            
            if len(data) > 10:
                output += f"\n... and {len(data) - 10} more rows\n"
            
            # 조인 설명 추가
            output += f"\n💡 This shows {table1} records with their related {table2} information"
            output += f"\n💡 Each row combines data from both tables where {left_key} matches"
            
            return output
            
    except Exception as e:
        # 에러 메시지 개선
        error_msg = str(e)
        if "column" in error_msg.lower():
            return f"❌ Column error: {error_msg}\nTry specifying join like: 'student_id=id' or 'course_id:id'"
        else:
            return f"❌ Join error: {error_msg}"


# Tool 9: 테이블 생성
@mcp.tool()
async def create_table(database: str, table_name: str, columns: str) -> str:
    """Create new table. Format: col1:type1,col2:type2 (types: text,number,date)"""
    if database not in DB_CONNECTIONS:
        return f"Database '{database}' not found"
    
    try:
        # 컬럼 정의 파싱
        col_defs = columns.split(',')
        sql_columns = []
        
        # DB 타입 감지
        db_url = DB_CONNECTIONS[database]["url"]
        is_postgres = 'postgresql' in db_url
        
        for col_def in col_defs:
            if ':' not in col_def:
                return "Invalid format. Use: column1:type1,column2:type2"
            
            col_name, col_type = col_def.split(':', 1)
            col_name = col_name.strip()
            col_type = col_type.strip().lower()
            
            # 간단한 타입 매핑
            if col_type in ['text', 'string', 'str']:
                sql_type = 'TEXT' if is_postgres else 'VARCHAR(255)'
            elif col_type in ['number', 'int', 'integer']:
                sql_type = 'INTEGER'
            elif col_type in ['float', 'decimal', 'money']:
                sql_type = 'DECIMAL(10,2)'
            elif col_type in ['date', 'datetime']:
                sql_type = 'DATE'
            elif col_type in ['bool', 'boolean']:
                sql_type = 'BOOLEAN'
            elif col_type == 'id':
                if is_postgres:
                    sql_type = 'SERIAL PRIMARY KEY'
                else:
                    sql_type = 'INT AUTO_INCREMENT PRIMARY KEY'
            else:
                sql_type = 'TEXT'  # 기본값
            
            # PRIMARY KEY가 이미 포함된 경우가 아니면 컬럼 추가
            if 'PRIMARY KEY' in sql_type and col_name != 'id':
                sql_columns.append(f"{col_name} {sql_type}")
            elif col_name == 'id' and 'PRIMARY KEY' not in sql_type:
                sql_columns.append(f"{col_name} {sql_type} PRIMARY KEY")
            else:
                sql_columns.append(f"{col_name} {sql_type}")
        
        # CREATE TABLE 쿼리 생성
        create_sql = f"CREATE TABLE {table_name} (\n  " + ",\n  ".join(sql_columns) + "\n)"
        
        engine = create_engine(DB_CONNECTIONS[database]["url"])
        
        # 테이블 생성 실행
        with engine.begin() as conn:
            # 테이블이 이미 존재하는지 확인
            inspector = inspect(engine)
            existing_tables = inspector.get_table_names()
            
            if table_name in existing_tables:
                return f"❌ Table '{table_name}' already exists in database '{database}'"
            
            # 테이블 생성
            conn.execute(text(create_sql))
            
            output = f"✅ Successfully created table '{table_name}' in database '{database}'\n\n"
            output += "Table structure:\n"
            for col_def in col_defs:
                col_name, col_type = col_def.split(':', 1)
                output += f"  • {col_name.strip()}: {col_type.strip()}\n"
            
            output += f"\n💡 Use 'show_data' to view the table (initially empty)"
            output += f"\n💡 Use 'add_data' to insert records"
            
            return output
            
    except Exception as e:
        return f"Create table error: {str(e)}"


if __name__ == "__main__":
    mcp.run(transport="stdio")