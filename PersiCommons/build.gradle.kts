/*
 * This file was generated by the Gradle 'init' task.
 */

plugins {
    `java-library`
    `maven-publish`
}

repositories {
    mavenLocal()
    maven {
        url = uri("https://repo.maven.apache.org/maven2/")
    }
}

dependencies {
    api("org.apache.commons:commons-lang3:3.12.0")
    api("org.apache.poi:poi:5.3.0")
    api("org.apache.poi:poi-ooxml:5.3.0")
}

group = "PersiCommons"
version = "1.0.0"
description = "Persi Commons"
java.sourceCompatibility = JavaVersion.VERSION_17

publishing {
    publications.create<MavenPublication>("maven") {
        from(components["java"])
    }
}
