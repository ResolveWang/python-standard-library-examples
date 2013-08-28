## 7.5 sqlite3 - Embedded Relational Database
import sqlite3, os, sys, csv, itertools
import logging, threading, time
# literal_eval evaluates a string value to a Boolean "True" becomes True etc.
from ast import literal_eval
# closing closes things that need to be closed, whenever they are supposed to close.
from contextlib import closing

try: # cPickle is fast but not always available
    import cPickle as pickle
except:
    import pickle

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s (%(threadName)-10s) %(message)s"
    )
    
# this is the database used for most of this demo, and the schema for it below.

#Column      Type    Description
# name        text    project name
# description text    long project description
# deadline    date    due date for the entire project

#Column         Type        Description
# id             number      unique task identifier
# priority       integer     numerical property; lower is more important
# details        text        full task details
# status         text        task status( new, pending, done, or cancelled)
# deadline       date        due date for the task
# completed_on   date        when was the task completed
# project        text        name of the project for this task

# this can all be defined via DDL (data definition language) and written to a file
# it could also just be saved to a file in some other manner (like with a text editor),
# or it can be loaded from memory
        
schema = """-- Schema for to-do application examples
--projects are high-level activities made up of tasks
create table project (
    name        text    primary key,
    description text,
    deadline    date
);

-- Tasks are steps that can be taken to complete a project
create table task (
    id             integer  primary key     autoincrement   not null,
    priority       integer  default 1,
    details        text,
    status         text,
    deadline       date,
    completed_on   date,
    project        text     not null        references project(name)
);
"""
# this is the output format for the individual tasks when listed
# it comes up a lot in this file, so I thought it would be nice to have a single string to make changes on
task_fmt = '{:2d} ({:d}) {:50s} [{:8s}] ({:s})'

## 7.5.1 Creating a Database
def create_new_database( db_filename, schema_filename, add_starter_data=False ):
    """Creates a new database using the given db_filename and schema.""" 
    # An SQLite db is stored as a single file on the file system
    db_is_new = not os.path.exists(db_filename)
    schema_is_new = not os.path.exists(schema_filename)

    if db_is_new or schema_is_new:
        with closing( sqlite3.connect(db_filename) ) as conn:
            if db_is_new:
                print "Database was created."   
            else:
                print "Database already exists."

            if schema_is_new:
                # The next step is creating a schema
                with closing( open(schema_filename, 'w+' ) ) as schema_file:
                    schema_file.write(schema)
                print "  Schema was created."
            else: 
                print "  Schema already exists."
        print

    # apply the schema (from file, in this case)
    # [though I'm overwriting the variable which already has the schema so this is not exactly useful]
    with closing( sqlite3.connect(db_filename) ) as conn:
        if (db_is_new or schema_is_new) :
            print "Applying Schema"
            with closing( open(schema_filename, 'r') ) as f:
                schema = f.read()
            # however you obtain the schema data, run it with executescript() on the db
            conn.executescript(schema)
            print " Schema Applied"
            print
            
            if add_starter_data:
                # since this block is only called when one/two of the two things required before you can insert data
                # did not exist prior to this instance of code, which means this data needs to get shovelled in.
                data = """
                insert into project ( name, description, deadline )
                values ( 'pystl', 'Python Standard Library by Example', '2013-08-31' );

                insert into task ( details, status, deadline, project )
                values ( 'Chapter 6', 'done', '2013-08-25', 'pystl' );

                insert into task ( details, status, deadline, project )
                values ( 'Chapter 7', 'pending', '2013-08-26', 'pystl' );

                insert into task ( details, status, deadline, project )
                values ( 'Chapter 8', 'new', '2013-08-27', 'pystl' );        
                """ 
                with closing( sqlite3.connect(db_filename) ) as conn:
                    print "Inserting Starter Data"
                    conn.executescript(data)
    
## 7.5.2 Retrieving Data
# to retrieve values, create a cursor from a database connection.
# A cursor provides a consistent view of data and is the primary means or transacting with a relational db
def fetch_project_tasks(project_name, fetch_type = 'all'):
    """Provides a bit of a clunky access to fetch certain specific items from the database"""
    with closing( sqlite3.connect(db_filename) ) as conn:
        # create cursor
        cursor = conn.cursor()
        # execute query through cursor
        cursor.execute("""
            select id, priority, details, status, deadline from task where project = ?
            """, (project_name, ) )
            
        if fetch_type == 'all':
            # read data from cursor
            for row in cursor.fetchall():
                task_id, priority, details, status, deadline = row
                print task_fmt.format( task_id, priority, details, status, deadline )
            print
        
        elif fetch_type == 'one':
            # there`s also a fetchone() that just fetches the first result,
            for row in cursor.fetchone():
                task_id, priority, details, status, deadline = row
                print task_fmt.format( task_id, priority, details, status, deadline )
            print
            
        elif fetch_type == 'many':
            # and a fetchmany(x) that just fetches [up to] x results.
            how_many = 5
            print how_many, "results:"
            for row in cursor.fetchmany( how_many ):
                task_id, priority, details, status, deadline = row
                print task_fmt.format( task_id, priority, details, status, deadline )
            
## 7.5.3 Query Metadata
# after execute() has been called, the cursor sets it's description attribute 
# to hold info about the data that will be returned by the fetch methods.
# the description = ( (column_name, type, display_size, internal_size, precision, scale, null_flag), ...)
# though, sqlite3 only returns the name, because it doesn't enforce size or type restraints
def display_columns(db_filename, project_name, type_detection):
    """Displays the columns in the task table for the project supplies,
    and then chains into showing each column's datatype if you ask it nicely"""
    with closing( sqlite3.connect(db_filename) ) as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
        select * from task where project = ?
        """, ( project_name, ) )
        
        print "\nTask table for %s has these columns:" % project_name
        for colinfo in cursor.description:
            print colinfo
        print
        
        show_column_types(db_filename, project_name, type_detection=type_detection)
        
## 7.5.4 Row Objects
# the default rows returned by the fetch methods are tuples
# this requires the caller to be responsible for the order and number of values in the query
# it is much easier to use a Row object and access values using their column names
# then the actual db structure can change all it wants without affecting the program

# Connection objects have a row_factory property that allows the calling code to control the type of object representing each row
# sqlite3 also includes a Row class intended to be used as a row_factory (wow)
def display_rows_via_objects(db_filename, project_name):
    """Demonstrates how to use the sqlite3.Row row_factory to get a Row object"""
    with closing( sqlite3.connect(db_filename) ) as conn:
        # Change the row_factory to use sqlite3.Row
        conn.row_factory = sqlite3.Row
        
        cursor = conn.cursor()
        
        cursor.execute("""
        select name, description, deadline from project
        where name = ?
        """, ( project_name, ) )
        
        p_name, description, deadline = cursor.fetchone()
        print "Project details for %s (%s) [%s]" % ( description, p_name, deadline )
        
        cursor.execute("""
        select id, priority, details, status, deadline from task 
        where project = ?
        order by deadline
        """, ( p_name, ) )
        
        for row in cursor.fetchmany(5):
            print row
            # read data from cursor using the Row object
            print task_fmt.format(  row['id'], row['priority'], row['details'], row['status'], row['deadline'] )
        print
        
## 7.5.5 Using Variables with Queries
# the proper way to use dynamic values in queries is with host variables
# Positional Arguments are indicated must match in number to the arguments provided
# I read ahead and have been doing this for this whole file because I knew merging strings wasn't good
    # Positional arguments are indicated with ?s
    
# Named Parameters are useful in more complex queries and especially when values are used more than once
def named_parameters(db_filename, project_name):
    """Simple example showing the use of named parameters in sql queries"""
        # Names parameters are indicated like :param_name
    with closing( sqlite3.connect(db_filename) ) as conn:
        # Change the row_factory to use sqlite3.Row
        conn.row_factory = sqlite3.Row
        
        cursor = conn.cursor()
        
        cursor.execute("""
        select name, description , deadline from project
        where name = ?
        """, ( project_name, ) )
        p_name, description, deadline = cursor.fetchone()
        print "Project details for %s (%s) [%s]" % ( description, project_name, deadline )
        
        cursor.execute("""
        select id, priority, details, status, deadline from task 
        where project = :project_name
        order by deadline
        """, {'project_name':p_name} )  # see, here is the named parameter in use

        for row in cursor.fetchmany(5):
            # read data from cursor using the Row object
            print task_fmt.format(  row['id'], row['priority'], row['details'], row['status'], row['deadline'] )   
        print

# query parameters can be used with select, insert, and update statements, as long as a literal value is legal in the context
def update_task_status(db_filename, id, status):
    """updates the status of the task with the specified id"""
    # run as `python 7.5-sqlite3.py update id status`
   
    with closing( sqlite3.connect(db_filename) ) as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
        select details, status from task 
        where id = ?
        order by deadline
        """, ( id, ) )
        
        t_details, t_status = cursor.fetchone()
        print "Updating status of task #%s - %s to [%s]" % ( id, t_details, status )

        cursor.execute( """
        update task
        set status = :status
        where id = :id
        """, { 'status':status, 'id':id } )
        
        conn.commit()
    
## 7.5.6 Bulk Loading
# use executemany() to apply the same set of SQL instructions to a large set of data
# this avoids complicating the code with loops and lets the underlying library apply loop optimization

def insert_data_from_csv(data_filename):
    """Reads a CSV file and imports that data into the task table"""
    #  run as `python 7.5-sqlite3.py insert data_file.csv`
    SQL = """
    insert into task (details, priority, status, deadline, project)
    values (:details, :priority, :status, :deadline, :project)
    """
    
    with closing( open( data_filename, 'r' ) ) as csv_file:
        # create a csv.DictReader to handle the data
        csv_reader = csv.DictReader(csv_file)
        
        with closing( sqlite3.connect(db_filename) ) as conn:
            cursor = conn.cursor()
            cursor.executemany(SQL, csv_reader)
            
            conn.commit()
               

## 7.5.7 Defining New Column Types
# SQLite only supports integer, floating point, or text columns
# though it only comes with a few data types internally
# sqlite3 has the ability to store any type of Python data
# if properly defined

# conversion for types supported beyond the base three is enabled in the db connection by using the detect_types flag.
# if the columns were declared using the desired type when the table was defined, PARSE_DECLTYPES will provide them
def show_column_types(db_filename, project_name, type_detection=None):
    """Displays column datatypes"""
    if type_detection == False:
        print "Without type detection:"
        with closing( sqlite3.connect(db_filename) ) as conn:
            show_deadline(conn, project_name)
    
    if type_detection == True:
        print "With type detection:"
        with closing( sqlite3.connect(
            db_filename, 
            detect_types=sqlite3.PARSE_DECLTYPES
        )) as conn:
            show_deadline(conn, project_name)
            
def show_deadline(conn, project_name):
    """Demonstrates the use of sqlite3's converters for date and datetime"""
    sql = """
    select id, details, deadline from task
    where project = ?
    """
    columns = ['id', 'details', 'deadline']
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(sql, [project_name,] )
    row = cursor.fetchone()
    # sqlite3 provides converters for date and timestamp columns, using Python's datetime.date and datetime.datetime
    for col in columns:
        print ' %-8s  %-30s %s' % (col, row[col], type( row[col] ))

# To register a new type with sqlite3, two functions must be registered
# The -adapter- takes the Python object as input andreturns a byte-string that can be stored in the database.
# The -converter- receives the string and returns a Python object
# register them to sqlite3 with register_adapter() and register_converter()
def adapter_function(obj):
    """Convert from in-memory Python object to storage representation"""
    print 'adapter_function(%r)\n' % obj
    return pickle.dumps(obj)
    
def converter_function(data):
    """Convert from storage representation to Python object"""
    print 'converter_function(%r)\n' % data
    return pickle.loads(data)
    
class MyDataObject(object):
    """Simple object"""
    def __init__(self, arg):
        self.arg = arg
    def __str__(self):
        return 'MyDataObject(%r)' % self.arg
        
def demo_object_registration( db_filename )  :   
    """Demonstrates the effects of registering a Python object adapter/converter for sqlite3"""
    # register the functions for manipulating the type
    sqlite3.register_adapter( MyDataObject, adapter_function )
    # notice MyDataObject vs. "MyDataObject"
    sqlite3.register_converter( "MyDataObject", converter_function )
        

    # create some objects to save
    # use a list of tuples so the sequence can be passed directly to executemany()
    to_save = [ (MyDataObject('This is a value to save.'),),
                (MyDataObject(42),),
              ]
    with closing( sqlite3.connect( 
        db_filename, detect_types=sqlite3.PARSE_DECLTYPES 
    ) ) as conn:
        # createa a table with a column of type MyDataObject
        conn.execute("""
        create table if not exists obj(
        id      integer         primary key autoincrement   not null,
        data    MyDataObject
        )
        """)
        
        cursor = conn.cursor()
        
        # Insert the objects into the db
        cursor.executemany("""
        insert into obj (data)
        values (?)""", to_save )
        
        # Query the database for objects just saved
        cursor.execute("""  select id, data from obj    """)
        
        for obj_id, obj in cursor.fetchall():
            print 'Retrieved %s type:%r (id:%d)' % ( str(obj), type(obj), obj_id )
        print

## 7.5.9 Transactions
# With transactions enabled (by default) the database isn't change until committed to
def show_projects(conn):
    """Shows all projects in database"""
    cursor = conn.cursor()
    cursor.execute("    select name, description from project  ")
    for name, desc in cursor.fetchall():
        print '\t%s\t%s' % (name, desc)
    return
    
def demo_commit_to_database( db_filename ):
    """Demonstrates the effects of committing to databases, and how the transactional model means that until changes are committed they won't be seen by other users and can be rolled back."""
    with closing( sqlite3.connect( 
        db_filename, detect_types=sqlite3.PARSE_DECLTYPES 
    ) ) as conn1:
        print "Before changes to conn1:"
        show_projects(conn1)
        new_project = ("bittchins", "Bitchins Design Website", "2013-09-01")
        # insert a new project
        cursor1 = conn1.cursor()
        cursor1.execute("""
        insert into project (name, description, deadline)
        values (?, ?, ?)
        """, new_project)
        
        print "\n(conn1) After changes:"
        show_projects(conn1)
        
        # Now another connection is created before the change is committed
        with closing( sqlite3.connect( 
        db_filename, detect_types=sqlite3.PARSE_DECLTYPES 
        ) ) as conn2:
            print "(conn2) Before commit to conn1:"
            show_projects(conn2)
        
        # commit the change to conn1
        conn1.commit()
        
        # then check what a new connection sees
        with closing( sqlite3.connect( 
        db_filename, detect_types=sqlite3.PARSE_DECLTYPES 
        ) ) as conn3:
            print "(conn3) After commit to conn1:"
            show_projects(conn3)
            
        try:
            # delete the new project
            cursor1.execute("""
            delete from project
            where name = ?
            """, ( new_project[0], ) )
            
            print "\n(conn1) After deleting project %s:"
            show_projects(conn1)
            
            raise RuntimeError("This is a calculated break, relax.")
        except RuntimeError, error:
            # discard the changes
            print "Error:", error
            conn1.rollback()
        else:
            # save the changes
            conn1.commit()
        print "\n(conn1) After rollback:"
        show_projects(conn1)
        
        # No, for real, delete the new project
        cursor1.execute("""
        delete from project
        where name = ?
        """, ( new_project[0], ) )
        
        # Now another connection is created before the change is committed
        with closing( sqlite3.connect( 
        db_filename, detect_types=sqlite3.PARSE_DECLTYPES 
        ) ) as conn4:
            print "(conn4) Before committing deletion to conn1:"
            show_projects(conn4)
        
        # commit the change to conn1
        conn1.commit()
        
        # then check what a new connection sees
        with closing( sqlite3.connect( 
        db_filename, detect_types=sqlite3.PARSE_DECLTYPES 
        ) ) as conn5:
            print "\n(conn5) After deleting project %s (FOR REAL):" % new_project[0]
            show_projects(conn5)
        
## 7.5.10 Isolation Levels
# sqlite3 supports isolation levels of:
    # DEFERRED - Locks the database only once a change has begun. This is the default mode.
    # IMMEDIATE - Locks the database as soon as a change starts and prevents other cursors from making changes until the transaction is committed.
    # EXCLUSIVE - Locks to each reader and writer individually, blocking all other connections.
    # and None (aka autocommit) - Locks the db for the smallest possible amount of time, as every execute(0 call is committed immediately
def demo_isolation_levels( db_filename, isolation_level=False ):
    """Demonstrates the different isolation levels in sqlite3"""
    if isolation_level:
        isolation_levels = [isolation_level, ]
    else:
        isolation_levels = ["DEFERRED", "IMMEDIATE", "EXCLUSIVE", None]
    for isolation_level in isolation_levels:
        print "Isolation level:", isolation_level
        # the threads are synchronised using threading.Event
        ready = threading.Event()
        
        threads = [
            threading.Thread(name='Reader 1', target=demo_isolation_levels_reader, args=(db_filename, isolation_level, ready)),
            threading.Thread(name='Writer 1', target=demo_isolation_levels_writer, args=(db_filename, isolation_level, ready)),
            threading.Thread(name='Reader 2', target=demo_isolation_levels_reader, args=(db_filename, isolation_level, ready)),
            threading.Thread(name='Writer 2', target=demo_isolation_levels_writer, args=(db_filename, isolation_level, ready) ),
        ]
        
        [ t.start() for t in threads ]
        
        time.sleep(1)
        logging.debug("Setting ready")
        ready.set()
        
        [ t.join() for t in threads ]

def demo_isolation_levels_writer( db_filename, isolation_level, ready ):
    """Connects to and makes a minor change to the task table"""
    my_name = threading.currentThread().name
    with closing( sqlite3.connect( db_filename, isolation_level=isolation_level ) ) as conn:
        cursor = conn.cursor()
        # make a change to the db and see what happens in this isolation level
        cursor.execute("""update task set priority = priority + 1""")
        logging.debug("Waiting to sync")
        ready.wait() # synchronize threads
        logging.debug("Pausing")
        time.sleep(1)
        if isolation_level:
            conn.commit()
        logging.debug("Changes committed")
    return

def demo_isolation_levels_reader( db_filename, isolation_level, ready ):
    """Reads all items in the task table after waiting for sync"""
    my_name = threading.currentThread().name
    with closing( sqlite3.connect( db_filename, isolation_level=isolation_level ) ) as conn:
        cursor = conn.cursor()
        logging.debug("Waiting to sync")
        ready.wait() # synchronize threads
        logging.debug("Wait over")
        cursor.execute("""  select * from task  """)
        logging.debug("Select executed")
        results = cursor.fetchall()
        logging.debug("Results fetched")
    return
    

    


            
## Function Controls
if __name__ == '__main__':
    # check for special commands as arguments
    arg_command = sys.argv[1] if len(sys.argv) >= 2 else None
    if arg_command is None:
        print "No command entered."
    elif arg_command == 'create_db':
        # create a new database file using the supplied file locations
        # if any filename that doesn't exist is given, it will be created
        # if a schema filename that doesn't exist is given the schema from the book will be created
        try:
            db_filename = sys.argv[2]
            schema_filename = sys.argv[3]
        except IndexError:
            print "You must specify both a db filename and a schema filename, though neither has to exist yet."
            raise
        create_new_database( db_filename, schema_filename )
    elif arg_command == 'create_demo_db':
        # if you want the database to be populated with sample data matching the book's schema use this function instead
        try:
            db_filename = sys.argv[2]
            schema_filename = sys.argv[3]
        except IndexError:
            print "You must specify both a db filename and a schema filename, though neither has to exist yet."
            raise
        create_new_database( db_filename, schema_filename, True )
        
    elif arg_command == 'columns':
        # display the columns in the task table.
        try:
            db_filename = sys.argv[2]
        except IndexError:
            print "You must specify the db to read from."
            raise
        try:
            project_name = sys.argv[3]
        except IndexError:
            print "You should specify the project name."
            project_name = '*' # defaults to all
        try:
            type_detection = literal_eval(sys.argv[4])
        except ValueError:
            print "\nYou've entered a non-boolean value for type detection.  You might have misspelled True or False (or None).  I'm going to set it to None so you don't get an error.  Please try again - type detection failed"
            type_detection = None
        except IndexError:
            print "\nYou can specify if you want to see the data types by adding a boolean value as the fourth argument. setting type_detection to False will show you the types as stored in the db, and True will show you the types as understood by sqlite3 - type detection failed"
            type_detection = None
        else:
            print "Else t_d", type_detection
        
        display_columns( db_filename, project_name, type_detection )
        
    elif arg_command == 'object_rows':
        # display the rows, like fetch, but using objects instead of tuples.
        try:
            db_filename = sys.argv[2]
            project_name = sys.argv[3]
        except IndexError:
            print "The arguments that must be given to this function are the db filename, and the project name."
            raise
        display_rows_via_objects( db_filename, project_name )
        
    # there are a few options when it comes to asking for the fetch commands
    elif arg_command == 'fetch' and len(sys.argv) == 3:
        # default to fetchall() if no second argument is passed
        try:
            project_name = sys.argv[2]
        except IndexError:
            print "Please provide a project name"
            raise
        fetch_project_tasks( project_name, 'all' )
    elif arg_command == 'fetch':
        # otherwise, pass in the second argument as the fetch_type
        try:
            project_name = sys.argv[2]
            fetch_type = sys.argv[3]
        except IndexError:
            print "This error shouldn't be possible."
            fetch_type = 'all'
        finally:
            fetch_project_tasks( project_name, fetch_type )
    
    elif arg_command == 'insert':
        # insert the data from the csv file specified
        try:
            csv_file_location = sys.argv[2]
        except IndexError:
            print "This function requires a csv file of data to insert"
            raise
        insert_data_from_csv( csv_file_location )
        
    elif arg_command == 'update':
        # update the status of the indicated task
        try:
            db_filename = sys.argv[2]
        except IndexError:
            print "You must specify the database file to use"
            raise
        try:
            task_id = int( sys.argv[3] )
        except IndexError:
            print "You must specify a task to alter"
            raise
        try:
            new_task_status = sys.argv[4]
        except IndexError:
            print "No status was specified, updating status to None"
            new_task_status = None
            
        update_task_status( db_filename,  task_id, new_task_status )
        
    elif arg_command == 'demo_new_datatype':
        # display the columns in the task table.
        try:
            db_filename = sys.argv[2]
        except IndexError:
            print "You must specify the db to read from."
            db_filename = 'data/7.5-sqlite3_datatypedemo.db'
        demo_object_registration( db_filename )
        print "This is just a demo, nothing was written to the database file"
        
    elif arg_command == 'demo_commit':
        # demonstrate the intricacies of committing and rolling back changes.
        try:
            db_filename = sys.argv[2]
        except IndexError:
            db_filename = 'data/7.5-sqlite3_to-do.db'
        demo_commit_to_database( db_filename )
        print "This is just a demo, but it may have left some traces in the db file. Specifically, if you specified a db file that didn't previously exist, it now does."
    elif arg_command == 'demo_isolation':
        # show the differences in isolation levels
        try:
            db_filename = sys.argv[2]
        except IndexError:
            db_filename = 'data/7.5-sqlite3_to-do.db'
        try:
            isolation_level = sys.argv[3]
        except IndexError:
            isolation_level = False
        demo_isolation_levels( db_filename, isolation_level )
        print "This may have changed the db."    
    else:
        print "Command not recognized."
