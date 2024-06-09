
from tkinter import filedialog
import os
import csv
import sqlite3
# https://stackoverflow.com/questions/70937038/group-by-works-with-select-columns-not-in-group-by

def select_file() -> str:
    '''
    Function selecting windows directory with .csv files exported from the program.
    '''
    file_path = filedialog.askdirectory(title="Select the directory with exported .csv files")
    assert len(file_path) != 0, 'No file was chosen'
    return file_path


def parse_range_string(range_string):
    '''
    Function changes the comma and dash notation of a range to a list of elements
    '''
    items = []
    ranges = range_string.split(',')

    for r in ranges:
        if '-' in r:
            start = int(r.split('-')[0])
            end = int(r.split('-')[1])
            items.extend(range(start, end + 1))
        else:
            items.append(int(r))

    return items

if __name__=='__main__':

    print('Please select a directory with .csv files exported')
    dir_path = select_file()
    files_list = os.listdir(dir_path)
    member_results_file: str = None
    member_sections_file: str = None
    for item in files_list:
        if item.startswith("Design Ratios on Members by Member ! Steel Design !"):
            member_results_file = item
        if item == "Sections.csv":
            member_sections_file = item

    # Create SQLite db or connect to an existing one
    db = sqlite3.connect('RFEM_results.db')
    cur = db.cursor()

    # Purge existing DB data
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    if len(cur.fetchall()) > 1:
        cur.execute('DROP TABLE IF EXISTS Steel_Design')
        cur.execute('DROP TABLE IF EXISTS Sections')
        # TODO maybe use drop schema?



    # TODO add option for member sets
    # Retrieve clear data from Steel_Design CSV file
    member_results_path: str = '{}{}{}'.format(dir_path, os.sep, member_results_file)
    with open(member_results_path, 'r', encoding='utf-8-sig') as f:
        results = csv.reader(f, delimiter=";")

        # Get content of headlines
        headline1 = next(results)
        headline2 = next(results)

        # Rename content of headlines to custom column titles
        col0_Member_no = headline1[0].replace(' ','_').replace('.','')
        col1_Location_x = f'{headline1[1]}_{headline2[1].split(" ")[0]}'
        col2_Stress_Point_no = f"{headline1[2]}_{headline2[2].replace(' ','_').replace('.','')}"
        col3_Design_Situation_name = f'{headline1[3]}_{headline2[3]}'
        col4_Load_Combination_no = f"{headline1[4]}_{headline2[4].replace('.','')}"
        col5_Design_Check_ratio = f"{headline1[5].replace(' ','_')}_{headline2[5].split(' ')[0]}"
        col6_Design_Check_type = f"{headline1[5].replace(' ','_')}_{headline2[6]}"
        col7_Design_Check_description = f"{headline1[5].replace(' ','_')}_{headline2[7]}"

        headlines: list[str] = [col0_Member_no,
                            col1_Location_x,
                            col2_Stress_Point_no,
                            col3_Design_Situation_name,
                            col4_Load_Combination_no,
                            col5_Design_Check_ratio,
                            col6_Design_Check_type,
                            col7_Design_Check_description]


        # Skip non data rows and retrieve data
        data: list[list[str]] = []
        members_total = 0
        for i, line in enumerate(results):
            if line[1].find('|') >= 0:
                continue
            if len(line[1]) == 0:
                continue
            members_total = int(line[0])
            data.append((line))


    # Create Steel_Design Table
    table_columns: str = ''
    for col in headlines:
        table_columns += f'{col} TEXT, \n'
    table_columns = table_columns[:-3]
    sql: str = f'''
        CREATE TABLE Steel_Design (
            result_id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            {table_columns}
            ) ;'''
    cur.execute(sql)


    # Populate Steel_Design table
    table_columns: str = ''
    for col in headlines:
        table_columns += f'{col}, \n'
    table_columns = table_columns[:-3]
    sql = f'''INSERT INTO Steel_Design ({table_columns})
                VALUES (?,?,?,?,?,?,?,?);'''
    cur.executemany(sql, data)


    # Distinguish values of non-numeric results in Design_Check_Ratio columns
    cur.execute("""SELECT DISTINCT Design_Check_Ratio FROM Steel_Design
                    ORDER BY Design_Check_Ratio DESC;""")
    non_numeric_ratio_val = []
    for result in cur:
        result_value = result[0].replace('.','')
        if result_value.isnumeric() is False:
            non_numeric_ratio_val.append(result_value)


    # Create a list containing strings of non-numeric results
    sql_non_numeric_values:str = ''
    for item in non_numeric_ratio_val:
        sql_non_numeric_values += f" \'{item}\',"
    sql_non_numeric_values= sql_non_numeric_values[:-1]


    # Create a list of Member Numbers of Members having non-numeric results
    cur.execute(f"""SELECT DISTINCT Member_No FROM Steel_Design
                    WHERE Design_Check_Ratio IN ({sql_non_numeric_values});""")
    members_containing_warning_or_error = []
    for i, result in enumerate(cur):
        members_containing_warning_or_error.append((result))


    # Add a new column representing if a Member has non-numeric results or not
    cur.execute('ALTER TABLE Steel_Design ADD Contains_Warning_or_Error INTEGER DEFAULT 0')


    # Add a value of 1 (True) for Members from a prepared list
    sql: str = ''' UPDATE Steel_Design
                    SET Contains_Warning_or_Error = 1
                        WHERE Member_NO = ?'''
    cur.executemany(sql, members_containing_warning_or_error)


    # Delete rows which have non-numeric values in Design_Check_Ratio column
    cur.execute(f'DELETE FROM Steel_Design WHERE Design_Check_Ratio IN ({sql_non_numeric_values});')






    # Create a list of members and their maximal value of Design_Check_Ratio
    cur.execute('''SELECT Member_No, max(cast(Design_Check_Ratio as real)) FROM Steel_Design
                    GROUP BY Member_No ORDER BY cast(Member_No as integer)''')
    member_ratio_max: list[list]  = []
    for result in cur:
        result_list = [(result[0]), float(result[1])]
        member_ratio_max.append(result_list)


    # Create a list of members which max value of Design_Check_Ratio is caused by Stability check
    cur.execute('''SELECT Member_No, max(cast(Design_Check_Ratio as real)), Design_Check_Description
                    FROM Steel_Design WHERE Design_Check_Description LIKE "Stability%" 
                    GROUP BY Member_No ORDER BY cast(Member_No as integer)''')
    member_stability_max: list[list] = []
    for result in cur:
        result_list = [(result[0]), float(result[1])]
        member_stability_max.append(result_list)


    # Add a new column representing if a Member has
    # a max Design Check value caused by Stability check
    cur.execute('''ALTER TABLE Steel_Design
                    ADD Ratio_max_Design_Check_to_Stability INTEGER DEFAULT 0''')



    # Calculate a ratio of Stability check value to max Design check value for every member
    ratios_list = []
    innerloop_range = len(member_stability_max)
    innerloop_maxval = member_stability_max[len(member_stability_max)-1]
    startpoint = 0
    for max_list in member_ratio_max:
        if int(max_list[0]) > int(innerloop_maxval[0]):
            # cannot use break statement, because in case of repeating datasets
            # some of the data will be ignored
            continue

        for j in range(startpoint, innerloop_range, 1):
            stability_list = member_stability_max[j]

            if stability_list[0] > max_list[0]:
                break

            if max_list[0] == stability_list[0]:
                if max_list[1] == 0:
                    max_list[1] = 0.001

                ratios_list.append([round( (stability_list[1]/max_list[1]) , 3), max_list[0]])
                startpoint = j+1
                break


    # Add the calculated ratio value for all Members
    sql: str = ''' UPDATE Steel_Design
                    SET Ratio_max_Design_Check_to_Stability = ?
                    WHERE Member_NO = ?'''
    cur.executemany(sql, ratios_list)



    #=-=-=-=-=-=-=-=-=-=-=-=-=-=#=-=-=-=-=-=-=-=-=-=-=-=-=-=


    # Retrieve clear data from Sections CSV file
    member_sections_path: str = '{}{}{}'.format(dir_path, os.sep, member_sections_file)
    with open(member_sections_path, 'r', encoding='utf-8-sig') as f:
        sections = csv.reader(f, delimiter=';')

        # Get content of headlines
        headline1 = next(sections)
        headline2 = next(sections)

        # Rename content of headlines to custom column titles
        col0_Section_No = headline1[0].replace(' ','_').replace('.','')
        col1_Section_Name = f"{headline2[1].replace(' ','_')}"
        col2_Assigned_to_Members = f"{headline2[2].replace(' ','_').replace('.','')}"
        col3_Material = f'{headline2[3]}'

        headlines: list[str] = [col0_Section_No,
                            col1_Section_Name,
                            col2_Assigned_to_Members,
                            col3_Material]

        # Retrieve data and parse rages defined in file
        data: list[list[str]] = []
        for i, row in enumerate(sections):
            line = [row[0], row[1], row[2], row[3]]
            line[2] = parse_range_string(line[2])
            data.append((line))


    # Parse Sections data into SQL Table form
    sections_data: list[list] = []
    for member_number in range(1, members_total+1):
        for row in enumerate(data):
            i = row[0]
            result_row = []
            if member_number in data[i][2]:
                result_row = [member_number, data[i][0], f"{data[i][0]}: {data[i][1]}", data[i][3]]
            if len(result_row) != 0:
                sections_data.append(result_row)


    # Create and Sections Table
    sql: str = f'''
        CREATE TABLE Sections (
            result_id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            Member_No TEXT,
            {headlines[0]} TEXT,
            {headlines[1]} TEXT,
            {headlines[3]} TEXT
            ) ;'''
    cur.execute(sql)


    # Populate Sections Table
    sql = f'''INSERT INTO Sections (Member_No, {headlines[0]}, {headlines[1]}, {headlines[3]})
                VALUES (?,?,?,?);'''
    cur.executemany(sql, sections_data)


    # Extract all of the useful data from database
    sql = '''SELECT
                cast(sd.Member_No as integer) as Member_No,
                Section_Name,
                max(cast(sd.Design_Check_Ratio as real)) as Design_Check_Ratio,
                Contains_Warning_or_Error,
                Ratio_max_Design_Check_to_Stability,
                Loading_No,
                Design_Check_Description
            FROM Steel_Design as sd
            JOIN Sections as s on sd.Member_No = s.Member_No
            GROUP BY sd.Member_No
            ORDER BY s.Section_Name, cast(sd.Member_No as integer); '''


    # Create Results viewtable
    view = f'''CREATE VIEW IF NOT EXISTS Results AS {sql} '''
    cur.execute(view)


    # Perform analysis on the database
    # TODO show most common Design_Check_Description for max value of design
    OPTIMISATION_LIMIT = 0.85
    sql = f'''
            SELECT 
                Section_Name, 
                count(CASE WHEN Design_Check_Ratio >= 1 THEN 1 END) as Number_of_failing_members,
                CASE 
                    WHEN count(CASE WHEN Design_Check_Ratio >= 1 THEN 1 END) > 0 THEN 'Section_is_UNSAFE'
                    WHEN count(CASE WHEN Design_Check_Ratio >= 1 THEN 1 END) = 0 THEN 'Section_is_Safe'
                    ELSE 'error'
                END AS Section_Safety,
                round(avg(CASE WHEN Design_Check_Ratio < 1 THEN Design_Check_Ratio END),3) as Average_Design_Check_for_non_failing_members,
                CASE
                    WHEN avg(CASE WHEN Design_Check_Ratio < 1 THEN Design_Check_Ratio END) >= {OPTIMISATION_LIMIT} THEN 'Section_is_optimally_designed'
                    WHEN avg(CASE WHEN Design_Check_Ratio < 1 THEN Design_Check_Ratio END) < {OPTIMISATION_LIMIT} THEN 'Section_CAN_BE_OPTIMISED'
                    ELSE 'error'
                END AS Section_Optimization
                FROM Results
                GROUP BY Section_Name
            '''
    cur.execute(sql)
    for column in cur.description:
        print(column[0], end=' | ')
    print()
    for x in cur:
        print(x)


    # Commit changes to Database
    db.commit()

    # # Delete unused files
    # db.close()
    # db_filepath = "{}{}{}".format(os.getcwd(), os.sep, 'RFEM_results.db')
    # os.remove(db_filepath)