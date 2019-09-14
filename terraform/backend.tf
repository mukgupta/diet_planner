terraform {
    backend "remote" {
        organization = "Mukesh-Personal"
        workspaces {
            name = "diet-planner"
      }
  }
}