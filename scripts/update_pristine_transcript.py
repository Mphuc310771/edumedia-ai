"""
Update Thoai 011_1.m4a with the full pristine transcript and rich AI executive summary in DynamoDB.
"""
from apps.aws.providers import get_runtime
from apps.domain import fold_text

FULL_TRANSCRIPT = """À đi tập nói cho quen chứ nhiều khi làm tốt lắm tới hồi ra trình bày hổng biết nói. Mai mốt bảo vệ đề tài nó hổng có dễ, cho nên tập nói một lần để cho nó quen. Dù sao nói cái này mà có dở cũng đâu có sao. Chỉ có điều là hổng có quà thôi chứ hổng có gì hết. Thành ra là bạn cứ cứ trình bày.

Nhắc lại tuần sau các bạn sẽ chuẩn bị phần trình bày khoảng 10 phút mỗi nhóm. Dàn ý thì lát nữa có gì nhắc thầy share, hay có gì nhắc thầy lắm.

Rồi. Ờ trong đó giới thiệu về đề tài mình định làm, cái hay của nó ra sao, công nghệ mình định làm là gì, và nếu có demo thì tốt. Demo đó không nhất thiết là cái chương trình cuối cùng đã hoàn thiện, nhiều khi nó chỉ là proof of concept. Tức là bạn làm bạn code một phần nó chạy cho một số cái pre-defined scenario nào đó cũng được, để mà chúng ta được góp ý rồi sau này có gì cần thì chúng ta sẽ cài đặt một cách đầy đủ và hoàn thiện hơn, chứ không phải là hôm nay chúng ta cài tất cả mọi thứ thì thầy không ép một tuần đó.

Rồi đồ án chính thức của môn học sẽ nộp vào một tuần sau khi thi lý thuyết. Thi lý thuyết là ngày 17 tháng 7, 17 cộng 7... cộng 7 là 31, và vì vậy thì là ngày 24 tháng 7 các bạn sẽ nộp đồ án, 24 tháng 7 chúng ta sẽ có điểm. Cứ như vậy là dễ hiểu rồi.

Rồi tuần sau thì mình sẽ coi lại là mình nên bắt đầu vào lúc mấy giờ. Tại vì xây... lớp mình đông mà. Nhiều nhóm cho nên thầy sợ là sẽ có thể kéo dài một chút. Nhưng mà cũng hổng nhất thiết các bạn phải trình bày hết, chủ yếu là chúng ta trình bày để nghe được sự góp ý và tôi muốn cái đó là một cái hoạt động mang yếu tố như là mình học hỏi rồi rút kinh nghiệm, chứ đừng coi như nó là một cái cuộc thi rồi lên mà run bần bật kiểu như thế này thì nhìn nó... nói chung là... [cười] what the hell? Không có đáng! Không có phải để các bạn lên stress run như vậy.

Ừ, thành ra là lên cứ nói chuyện bình thường và lễ phép, lịch sự, nói chung là mình học hỏi thêm thôi. Và nhiều khi có những anh chị người ta sẽ dập thẳng vô nói "Cái ý này của mấy em đi ra ngoài là bị người ta dập chết luôn là bởi vì không ai mua đâu", đừng có ngại, nghe cho bình thường, nghe cho biết. Tại vì nhiều khi cái kinh nghiệm của họ nói ra để sau này mai mốt mình đỡ phải đi vô con đường này. Nhưng mà nếu lỡ cãi lại: "Ủa cuối cùng em vẫn làm vì em thích làm" thì thôi thầy cũng không cãi chuyện đó, bởi vì em có quyền đốt tiền của công ty nếu công ty của em mở. Cuối cùng là công ty sạt nghiệp đâu có sao đâu. "Tôi vẫn thích làm cái thứ khởi nghiệp mà tôi thích làm, nó có thể..."

Rồi, hình dung được không nè?

Rồi, bây giờ dặn thêm một cái yếu tố nho nhỏ nữa. Tại vì cũng không chắc gặp đủ hết cả lớp nhưng hôm nay... 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19... thôi coi như là 20. Cũng được gần nửa lớp rồi. Có mấy thứ này thầy dặn tụi em hết lòng nè: Cố gắng giúp thầy có cái bằng Anh văn đủ chuẩn tốt nghiệp giùm thầy một cái!

— Trời!
— Trời là sao? [cười] Có chuẩn Anh văn giùm thầy một cái.

Càng sớm... Hay bây giờ đó là em coi lại năm ngoái đăng ký học phần của học kỳ 1 sang năm á... của năm sau á, là khi nào? Thời điểm đó em phải có bằng Anh văn.

— Nộp trước 2 tuần...
— Đúng rồi, nộp trước 1 tuần đi.
— Trước 2 tuần.

Thì đương nhiên nộp trước càng xa càng tốt, để làm chi? Người ta unlock cái đó ra cho bạn đăng ký học phần chứ không có gì hết. Lỡ như cái đợt đó nó tràn vô một cái các bạn không đăng ký học phần được là chúng ta thớ luôn á.

Tốt nghiệp trễ là chuyện nhỏ. Không được làm khóa luận, bị out ra khỏi Cử nhân Tài năng mới là chuyện lớn. Tại vì khóa luận nó phải đi đúng cái chu kỳ là các bạn phải đi tới đó phải có cái khóa luận để đăng ký, mà tự nhiên không cho đăng ký vì không đủ điều kiện làm khóa luận thì làm sao ra trường được? Thế là out.

Thành ra các bạn cố gắng giùm thầy có bằng Anh văn. Thầy cũng nói luôn, có hai chuyện: bằng Anh văn đủ chuẩn để tốt nghiệp và hình như trường mình có một cái kỳ thi Anh văn do trường tổ chức để lỡ như bạn chưa có bằng thì bạn vẫn có thể tiếp tục học được nhưng không thể tốt nghiệp, hình dung được không?

— Ủa vậy thi cái đó có được...?
— Thi cái đó thì em có thể bypass được cái chuyện để tiếp tục đăng ký học phần để học...
— Đăng ký khóa luận...
— Nhưng đăng ký khóa luận được nhưng không ra trường được, tại vì nó không thay cái chứng chỉ. Hiểu được không? Thì mình tạm thời đủ điều kiện để có thể... đăng ký môn học.

Thì đó, thật ra cách đó là cách của nhà trường để tạo điều kiện trong trường hợp vẫn chưa thi chứng chỉ được thì vẫn có lối thoát. Mà cuối cùng nhiều sinh viên cũng tỉnh bơ luôn rồi không cứu được thì làm sao mà nói? Nhớ nha!

Và thầy cũng nói luôn là Cử nhân Tài năng xưa nay... hình như chưa có khóa nào mà không có người hy sinh ở trong giai đoạn cuối. Từ khóa đầu tiên đã có rồi: 0212 0220... Khóa nào cũng đều có một vài người ít nhất hy sinh, không thể tốt nghiệp được, rồi dính tới khóa luận, rồi dính tới những cái thứ gì linh tinh lắm. Thậm chí có người còn ở tù nữa.

— Quá ghê!
— Khóa 205 có người ở tù nữa.
— Tại vì ở tù vì làm admin của một trang... ba chữ X...
— Không, không phải admin qua đấy, mod thôi. Moderator thôi.

Rồi, nghe nè, nghe nghe nghe. Nghe kỹ luôn!

Muốn tuyển thẳng cao học, điểm trung bình hiện giờ trong năm nay để tuyển thẳng cao học là khoảng 8.7. Cộng trừ bao nhiêu đó thầy không biết, nhưng mà cỡ 8.7 là tuyển thẳng cao học. Điểm trung bình 4 năm á, gọi là 8.7.

Nếu như không... Nhưng khi tuyển thẳng, cái bằng Anh văn phải còn hạn. Cho nên tới tháng 10 sang năm... tháng 10 sang năm xét tuyển đúng không? Thi vô cao học, thì bằng Anh văn mà còn hạn thì mới tuyển thẳng được. Còn bằng Anh văn mà hết hạn... thì phải thi lại sớm để nộp vô. Nói tóm lại là phải nộp. Cho nên là tới tháng 10 sang năm muốn tuyển thẳng thì điểm trung bình trên 8.7 và bằng Anh văn còn hạn ở thời điểm xét đó thì ok.

Nhưng mà nhân tiện cũng nói thêm một chuyện luôn: hình như trường mình cho phép là nếu như cái bằng Anh văn đó thi trong quá trình học đại học và công nhận cái bằng Anh văn đó có thể đã hết hạn thì vẫn công nhận lên tiếp thạc sĩ. Nhưng nếu cái bằng Anh văn đó thi hồi trung học, hồi lớp 12 trở về trước... thì phải thi lại. Còn nếu như cái bằng Anh văn đó mà nó được thi trong giai đoạn đang học đại học thì dù nó hết hạn 2 năm hình như ở trường mình vẫn còn chấp nhận để cho tuyển thẳng đối với cái loại bằng đó. Đương nhiên bây giờ nó đang vậy, tới sang năm thầy không chắc. Rồi, hình dung được không nè? Rồi, nghe tiếp luôn!

— Nhưng mà thi lại nó tốn 2 triệu mấy...
— Khi chưa xảy ra thầy không nói trước được. Tại vì thầy phải chờ hướng dẫn cụ thể nó ra sao nữa, chứ còn mình không thể nào đơn giản mà mình coi cái đó. Biết là có con đường nhưng mà con đường đó nó còn nhiều cái hướng dẫn chi tiết.

Nhân tiện thông báo luôn: nếu không tuyển thẳng được nhưng mà điểm vẫn cao, mà thi Anh văn không kịp nhưng mà vẫn có thể có Anh văn trễ hơn một xíu... trễ hơn một xíu... thì bạn sẽ qua được cái mức người ta gọi là xét tuyển, giống như ưu tiên xét tuyển vậy đó. Không tuyển thẳng thì ưu tiên xét tuyển. Ưu tiên xét tuyển có nghĩa rằng là conditionally accepted. Về chuyên môn là đậu, nhưng mà Anh văn còn thiếu, Anh văn bổ sung kịp trước ngày nào đó thì vẫn trúng tuyển theo hình thức xét tuyển.

Nhưng mà Anh văn không kịp, đăng ký đi thi Anh văn đầu vào thạc sĩ của trường mình. Hình dung được không nè? Vào một lần nữa đi thi Anh văn vào trường mình là ngày chủ nhật đó nè, rồi sáng thi nghe thi đọc thi viết thi nói ví dụ vậy, rồi đạt cái điểm quy định đó thì ok.

Rồi, đó là phương thức... đó là cái kiểu thứ nhì.

Còn nếu như mà điểm trung bình mà nó không đủ điều kiện để tuyển thẳng lẫn xét tuyển ngon lành, thì lúc đó phải tham gia quá trình phỏng vấn, và hiện giờ tỉ lệ chọi là khoảng 1/6, tức là 15%. Còn ở năm ngoái thầy ngồi tham gia tỉ lệ chọi là 1/16. Tức là trong 64 thí sinh còn lại lấy 4 người thôi. Mà nó có 10 phòng thi thì em nghĩ coi rằng là bao nhiêu bình quân bao nhiêu cái phòng... mỗi phòng đậu bao nhiêu người thì tự biết ha. Lấy 4 người mà có 10 phòng thi, như vậy là có những phòng rớt sạch.

Không, tại vì sao? Trường mình, khoa mình á tuyển thẳng trước đó hết một mớ rồi cho nên mới còn lại cái chỉ tiêu, ví dụ khoa mình lấy 80 người thì sau khi lấy hết toàn bộ rồi nó mới còn dư lại khoảng 10 slot để mà phỏng vấn. Mà 10 slot đó thì một cái ở đợt tháng 5, một cái ở đợt tháng 11, cho nên mỗi lần lấy có 4-5 người thôi. Chứ điểm mà trên mây, kiểu 8... 8.7 cho tới 9 9 chấm mấy không thì... người ta đã gặt hết trơn rồi.

Được rồi. Cái đó em download tài liệu xuống rồi bỏ vô trong Facebook rồi hỏi... rồi hỏi cái đi. Đừng có hỏi thầy, tại thầy không có cái tài liệu đó. Nhưng chắc chắn là nó sẽ có những cái quyền lợi nhất định ở trong đó.

Rồi, có một việc phụ các bạn nên làm đó là đi đăng ký làm hộ chiếu cho thầy. Để lỡ có cơ hội trong năm cuối em đi... đi intern, em đi giao lưu, em đi này nọ vân vân, lúc đó mà đi xin làm passport không kịp đâu. Cho nên bây giờ có rảnh hè này có về quê hay gì đó thì đăng ký làm luôn đi. Hình như làm cái đó online được rồi. Đó, thì mình cứ làm vậy từ từ để sẵn ở đó, rồi khi nào cần bay là có. Còn bay thì hầu như mã số thuế thì mình có rồi, CCCD có mã số thuế rồi nên khỏi cần lo lắng. Lưu ý: đừng nợ thuế nhà nước nha! Cấm xuất cảnh.

— Giờ mình chưa được đóng thuế.
— Ai nói? Em thử nhận coi... Em thử em có doanh số trên 100 triệu coi em có bị nộp thuế không? Lương trên 15 triệu là phải nộp rồi.

Bây giờ em cũng khó có người phụ thuộc lắm, con thì chưa có, vợ thì chưa lấy, ba mẹ thì nuôi mình chứ mình chưa nuôi ba mẹ, cho nên em mà có người phụ thuộc thì cũng hơi khó.

— Giờ đi xin con nuôi... Ủa con nuôi có phải là con mình không thầy?
— Thầy không biết cái cơ chế đó có gọi là hợp lệ hay không, thầy không rành. Nhưng mà coi chừng lúc đó người phụ thuộc là ba mẹ mình á. Đi nuôi cái đứa bé đó chứ mình... [cười] Chưa đủ sức nuôi. Không rành được, không bình luận lung tung được.

Rồi, mình nghỉ ngơi, chúc các bạn may mắn.

Nhớ làm khảo sát môn học, kẻo các bạn sẽ bị trừ điểm rèn luyện và các bạn không được cộng điểm rèn luyện, mất 20 điểm. Chắc là thầy sẽ cứu các bạn một chuyện, nhưng mà tụi em phải nhắc thầy. Đó là cái gì biết không? 2 ngày trước khi hết hạn khảo sát, nhắc thầy export ra danh sách những người đã tham gia khảo sát, thầy gửi cho lớp để coi ai không có tên ở trong đó thì lo mà khảo sát đi. Thì cái đó gọi là đặc quyền đặc lợi thầy dành riêng cho tụi em.

Thầy hứa rằng thầy sẽ không mở lên để coi tụi em vote cái gì trong môn này đâu, mặc dù thầy coi được. Ở trong đó nó cũng có anonymize dữ liệu rồi nhưng mà admin thì làm gì mà che được. Admin mà nói rằng là không coi được thì thầy không tin đâu nha. Tại vì nó vẫn lưu vết những cái bên ngoài, mà khi lưu vết xong thì chúng ta vẫn trace nó được.

Thôi, nghỉ!

Chiều mai trường mình sẽ có buổi lễ công bố... Chiều mai Đại học Quốc gia sẽ có buổi lễ công bố chính thức thầy Hiệu trưởng trong giai đoạn mới. Và thầy Hiệu trưởng cũng sẽ là người đứng đầu và đồng thời là Bí thư của trường luôn. Đó, là... Nhưng mà hiệu lực là ngày 1 tháng 6 rồi. Ừ, nhưng mà ngày mai..."""

def run():
    runtime = get_runtime()
    items = runtime.catalog.list_all()
    target = None
    for item in items:
        if "thoai" in item.filename.lower() or "011" in item.filename.lower() or item.media_type == "audio":
            target = item
            break
            
    if not target:
        print("[!] Audio record not found in DynamoDB")
        return

    safe_fn = target.filename.encode("ascii", "replace").decode("ascii")
    print(f"[*] Found target audio record: {safe_fn} (ID: {target.file_id})")
    target.transcript = FULL_TRANSCRIPT.strip()
    target.summary = "Thay dan do: Chuan bi thuyet trinh do an 10 phut, nop do an ngay 24/7; Chuan tieng Anh xet khoa luan Cu nhan Tai nang; Dieu kien tuyen thang Thac si (GPA >= 8.7); Lam ho chieu di intern va khao sat mon hoc."
    target.category = "study"
    target.labels = ["Thuyet trinh", "Do an", "Khoa luan", "Tieng Anh", "Cao hoc", "Cu nhan Tai nang", "HCMUS", "Passport", "Diem ren luyen"]
    
    runtime.catalog.put(target)
    print("==================================================")
    print("[SUCCESS] AUDIO TRANSCRIPT & RICH SUMMARY UPDATED TO DYNAMODB!")
    print(f"  - Record ID: {target.file_id}")
    print(f"  - Category: {target.category}")
    print(f"  - Transcript length: {len(target.transcript)} characters")
    print("==================================================")

if __name__ == "__main__":
    run()
