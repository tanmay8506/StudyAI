from database.client import db

def delete_paper(upc):
    # This cascades to units and topics because of Supabase foreign keys, 
    # but we can explicitly delete them just in case.
    db.table('topics').delete().eq('upc', upc).execute()
    db.table('units').delete().eq('upc', upc).execute()
    db.table('papers').delete().eq('upc', upc).execute()
    print(f"Deleted {upc} successfully!")

if __name__ == "__main__":
    delete_paper('2352203601')
    delete_paper('2352283601')
