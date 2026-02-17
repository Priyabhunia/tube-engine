if __name__ == "__main__":
    import uvicorn
    from app.main import app

    uvicorn.run(app, host="127.0.0.1", port=8080)
