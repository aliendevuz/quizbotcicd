# Cloud fanidan topshiriq

Cloud fanidan CI/CD mavzusiga kelganmiz va github actions va AWS lambda ishtirokida bu jarayonni namuna sifatida o'qituvchiga ko'rsatishimiz kerak, ya'ni git push -> testing -> zip -> deploy to AWS lambda
Soddalikni saqlash uchun database ishlatmaymiz, shunchaki AWS lambdada python asosida ishlaydigan telegram bot qilamiz

telegram bot hech qanday state saqlamaydi db yo'q, shunchaki random quiz yuboradi, quiz_bank.json faylida esa yuborish uchun tayyor quizlar ro'yxati mavjud, e'tiborli bo'ling, bu aws_lambda uchun, shuning uchun main.py ni entry point sifatida lambda_handler funksiyasini ichidagi src/app.py ga user request yo'naltirilgan holda ishlaydigan qilib berishingiz kerak, kodlar tartibli va testable qilib yozilishi kerak, keyin kodlar tayyor bo'lganida pytest larni yozishingiz kerak, localda testlardan muvafaqqiyatli o'tganidan keyin .github/workflows/deploy.yml ichida main branchga trigger bo'lganida avval test qilib keyin AWS lambdaga zip'ni deploy qiladigan qilib script yozing

oxirida menga DEPLOY.md fayliga loyihani AWS ga joylab ishlaydigan holatga keltirish uchun end to end ko'rsatma yozing