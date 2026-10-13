from locust import HttpUser, task, between


class ApiUser(HttpUser):
    wait_time = between(0.2, 1.0)

    @task(3)
    def health(self):
        self.client.get("/health")

    @task(1)
    def sum_endpoint(self):
        self.client.post("/sum", json={"a": 10, "b": 32})
