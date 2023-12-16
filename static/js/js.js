function is_desc(asValue) {
    var regExp = /^([A-Za-z0-9()\/@*.,:!@#$%\s]{0,50})?$/;
    return regExp.test(asValue);
}
function is_password(asValue) {
    var regExp = /^[0-9a-zA-Z!@#$%^&*]{8,20}$/;
    return regExp.test(asValue);
}
function is_telephone(asValue) {
    // karena optional
    // Nomor telepon minimal 0 digit, maksimal 15 digit 
    var regExp = /^\d{0,15}$/;
    return regExp.test(asValue);
}
function is_name(asValue) {
    // boleh huruf dan angka, minimal 3 char, maksimal 15 char, 
    var regExp = /^[a-zA-Z0-9_-/\s]{3,20}$/;
    return regExp.test(asValue);
}
function is_email(asValue) {
    var regExp = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
    return regExp.test(asValue);
}
function is_foto(asValue) {
    //hanya menerima jpg, jpeg dan png
    var regExp = /^.*\.(jpg|jpeg|png)$/i;
    // ukuran maksimal 2MB
    var maxFileSize = 2000000; // 2MB
    return regExp.test(asValue.name.toLowerCase()) && asValue.size <= maxFileSize;
}