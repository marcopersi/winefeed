// Versions in a centralized block
val springContextVersion by extra("6.1.14")
val springBeansVersion by extra("6.0.12")
val springCoreVersion by extra("6.0.12")
val springTestVersion by extra("6.0.12")
val junitJupiterVersion by extra("5.10.0")
val slf4jVersion by extra("2.0.9")
val lombokVersion by extra("1.18.28")
val tikaVersion by extra("2.9.0")
val pdfboxVersion by extra("2.0.29")
val itextpdfVersion by extra("5.5.13.2")
val groovyVersion by extra("3.0.17")

plugins {
    `java-library`
    `maven-publish`
    idea
}
repositories {
    mavenLocal()
    mavenCentral()
}

dependencies {
    api("org.apache.commons:commons-lang3:3.12.0")

    // Spring Core dependencies
    implementation("org.springframework:spring-context:$springContextVersion")
    implementation("org.springframework:spring-beans:$springBeansVersion")
    implementation("org.springframework:spring-core:$springCoreVersion")

    // Optional: Spring Test dependencies if you need testing support
    testImplementation("org.springframework:spring-test:$springTestVersion")
    testImplementation("org.junit.jupiter:junit-jupiter:$junitJupiterVersion")

    // SLF4J for logging
    implementation("org.slf4j:slf4j-api:$slf4jVersion")
    implementation("org.slf4j:slf4j-simple:$slf4jVersion")

    // Lombok for reducing boilerplate code
    compileOnly("org.projectlombok:lombok:$lombokVersion")
    annotationProcessor("org.projectlombok:lombok:$lombokVersion")

    // Apache Tika for parsing functionalities
    implementation("org.apache.tika:tika-core:$tikaVersion")
    implementation("org.apache.tika:tika-parsers:$tikaVersion")

    // Apache PDFBox for PDF processing
    implementation("org.apache.pdfbox:pdfbox:$pdfboxVersion")

    // iText PDF Library (last freely available version)
    implementation("com.itextpdf:itextpdf:$itextpdfVersion")

    // JUNIT 5
    testImplementation("org.junit.jupiter:junit-jupiter:6.0.2")

    // Vino Domain
    implementation(project(":VinoDomain"))

    // Excel Util
    implementation(project(":PersiCommons"))

    implementation("org.codehaus.groovy:groovy:$groovyVersion")
    implementation("org.codehaus.groovy:groovy-ant:$groovyVersion")
    implementation("org.codehaus.groovy:groovy-xml:$groovyVersion")

    implementation("org.ccil.cowan.tagsoup:tagsoup:1.2.1")
}

tasks.test {
    useJUnitPlatform()
    testLogging {
        events("passed", "skipped", "failed")
    }
}

group = "VinoImporter"
version = "1.0.0"
description = "VinoImporter"
java.sourceCompatibility = JavaVersion.VERSION_17

publishing {
    publications.create<MavenPublication>("maven") {
        from(components["java"])
    }
}
