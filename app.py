from flask import Flask, jsonify, render_template
from flask_graphql import GraphQLView
from flask_cors import CORS
import graphene
from graphene import Mutation, ObjectType, String, ID, Field, InputObjectType
from flask_pymongo import PyMongo
from bson import ObjectId
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity

app = Flask(__name__)
CORS(app)

app.config['MONGO_URI'] = 'mongodb://localhost:27017/todo_app'
app.config['JWT_SECRET_KEY'] = 'your_jwt_secret_key'
jwt = JWTManager(app)
mongo = PyMongo(app)

class TodoItem(graphene.ObjectType):
    id = ID()
    title = String()
    description = String()
    time = String()
    image = String()

class TodoInputData(graphene.InputObjectType):
    title = String(required=True)
    description = String(required=True)
    time = String(required=True)
    image = String()

class Query(ObjectType):
    list_todos = graphene.List(TodoItem, description="Retrieve all To-Dos")

    @jwt_required()
    def resolve_list_todos(self, info):
        current_user = get_jwt_identity()

        
        todos = mongo.db.todos.find({"user_id": current_user})

        return [TodoItem(
            id=str(todo['_id']),
            title=todo['title'],
            description=todo['description'],
            time=todo['time'],
            image=todo['image']
        ) for todo in todos]

class AddTodoMutation(Mutation):
    class Arguments:
        input_data = TodoInputData(required=True)

    todo = Field(lambda: TodoItem)

    @jwt_required()
    def mutate(self, info, input_data):
        current_user = get_jwt_identity()

        new_todo = {
            "user_id": current_user,
            "title": input_data.title,
            "description": input_data.description,
            "time": input_data.time,
            "image": input_data.image,
        }
        result = mongo.db.todos.insert_one(new_todo)

        created_todo = mongo.db.todos.find_one({"_id": result.inserted_id})

        return AddTodoMutation(
            todo=TodoItem(
                id=str(created_todo['_id']),
                title=created_todo['title'],
                description=created_todo['description'],
                time=created_todo['time'],
                image=created_todo['image']
            )
        )

class RemoveTodoMutation(Mutation):
    class Arguments:
        todo_id = ID(required=True)

    status_message = String()

    @jwt_required()
    def mutate(self, info, todo_id):
        current_user = get_jwt_identity()

        result = mongo.db.todos.delete_one({"_id": ObjectId(todo_id), "user_id": current_user})

        if result.deleted_count > 0:
            return RemoveTodoMutation(status_message=f"Todo {todo_id} successfully deleted.")
        else:
            return RemoveTodoMutation(status_message=f"Todo {todo_id} not found or unauthorized.")

class Mutation(ObjectType):
    add_todo = AddTodoMutation.Field()
    remove_todo = RemoveTodoMutation.Field()

schema = graphene.Schema(query=Query, mutation=Mutation)

app.add_url_rule(
    "/graphql",
    view_func=GraphQLView.as_view("graphql", schema=schema, graphiql=True),
)

if __name__ == "__main__":
    app.run(debug=True)
